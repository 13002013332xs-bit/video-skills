"""Reusable zn-open-eco transport. No store, page, credentials or sending defaults.

Business scope and native selectors belong to the current round's adapter.
This module never retries a business action or falls back to another interface.
"""
import json
from pathlib import Path
import subprocess
import time
import uuid


class AgentError(RuntimeError):pass
class PendingToolCall(AgentError):pass
class IncompleteData(AgentError):pass
class NoProgress(AgentError):pass


def _text_payload(content):
    text=next((c.get('text','') for c in content if c.get('type')=='text'),'')
    try:return json.loads(text)
    except (ValueError,TypeError):return text


def _omitted(value):
    if isinstance(value,dict):
        return value.get('data_omitted') is True or 'parsed_json_preview' in value or any(_omitted(v) for v in value.values())
    if isinstance(value,list):return any(_omitted(v) for v in value)
    return False


class AgentClient:
    def __init__(self, *, browser_id, task_id, evidence_dir, runner=subprocess.run,
                 timeout=20, wait_seconds=10):
        if not browser_id or not task_id:raise ValueError('Bind the current browser_id and task_id')
        if not 0<wait_seconds<timeout<=60:raise ValueError('Require wait_seconds < timeout <=60')
        self.browser_id=str(browser_id);self.task_id=str(task_id)
        self.root=Path(evidence_dir);self.root.mkdir(parents=True,exist_ok=True)
        self.runner=runner;self.timeout=timeout;self.wait_seconds=wait_seconds
        self.last_content=[]

    def _pending(self,call_id,name,status):
        receipt={'browser_id':self.browser_id,'task_id':self.task_id,
                 'tool_call_id':call_id,'name':name,'status':status}
        path=self.root/('pending-'+call_id+'.json')
        path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
        return path

    def _dispatch(self,name,args):
        call_id='outreach-'+uuid.uuid4().hex
        argv=['zn-open-eco','agent','tool','--browser-id',self.browser_id,
              '--task-id',self.task_id,'--tool-call-id',call_id,'--name',name,
              '--arguments-json',json.dumps(args,ensure_ascii=False),'--wait-seconds',str(self.wait_seconds)]
        start=time.monotonic();status='error';code=None
        try:
            try:r=self.runner(argv,capture_output=True,text=True,timeout=self.timeout)
            except subprocess.TimeoutExpired:
                status='unknown-after-timeout'
                receipt=self._pending(call_id,name,status)
                raise PendingToolCall('Outcome unknown; inspect existing tool call before retry: '+str(receipt)) from None
            try:d=json.loads(r.stdout)
            except (ValueError,TypeError):raise AgentError('CLI returned invalid JSON; do not replay the action') from None
            status=d.get('status','error')
            error=d.get('error') or {}
            code=error.get('code')
            if error or d.get('output',{}).get('is_error'):
                raise AgentError(str(code or 'TOOL_ERROR')+': '+str(error.get('message','Tool reported an error')))
            if status in ('pending','queued','running'):
                receipt=self._pending(call_id,name,status)
                raise PendingToolCall('Tool still active; inspect its status, do not resubmit: '+str(receipt))
            if r.returncode or status!='succeeded':raise AgentError('Unexpected CLI outcome: '+str(status))
            self.last_content=d.get('output',{}).get('content',[])
            return _text_payload(self.last_content)
        finally:
            # Timing metadata only: no messages, JS, screenshots, credentials or returned lists.
            row={'time':time.time(),'elapsed_seconds':round(time.monotonic()-start,4),
                 'tool_call_id':call_id,'tool':name,'action':args.get('action'),
                 'status':status,'error_code':code}
            with (self.root/'agent-timing.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')

    def call(self,name,args):
        result=self._dispatch(name,args)
        observed=result
        for _ in range(2):
            required=observed.get('required_verification_call') if isinstance(observed,dict) else None
            if not required:return result
            if name!='browser' or required.get('action') not in ('snapshot','screenshot','visible_dom'):
                raise AgentError('Unexpected verification request; inspect schema before continuing')
            # Preserve the exact action AND parameters, including screenshot baseline.
            observed=self._dispatch('browser',required)
        if isinstance(observed,dict) and observed.get('required_verification_call'):
            raise AgentError('Verification did not clear; stop before another business action')
        return result

    def browser(self,action,params=None):
        return self.call('browser',{'action':action,**({'params':params} if params is not None else {})})

    def evaluate(self,js):
        payload=self.browser('evaluate',{'js':js,'download':False})
        result=payload.get('result',payload) if isinstance(payload,dict) else payload
        if isinstance(result,str):
            try:result=json.loads(result)
            except ValueError:pass
        if _omitted(result):raise IncompleteData('Preview/truncation is incomplete; use bounded extraction')
        return result


def read_batches(count,fetch):
    """Read a previously observed, stable row count in complete batches of <=5."""
    if type(count) is not int or count<0:raise ValueError('Observed nonnegative row count required')
    rows=[]
    for start in range(0,count,5):
        stop=min(start+5,count);part=fetch(start,stop)
        if not isinstance(part,list) or len(part)!=stop-start or _omitted(part):
            raise IncompleteData('Expected complete bounded rows; stop without using a preview')
        rows.extend(part)
    return rows


class ProgressGuard:
    """Bound identical observations; a stall is not proof the dataset is exhausted."""
    def __init__(self,max_unchanged=2):
        if type(max_unchanged) is not int or max_unchanged<1:raise ValueError('Positive bound required')
        self.limit=max_unchanged;self.previous=None;self.unchanged=0
    def observe(self,count,position):
        current=(count,position)
        self.unchanged=self.unchanged+1 if current==self.previous else 0
        self.previous=current
        if self.unchanged>=self.limit:raise NoProgress('No new cards or displacement; inspect current loading/end/pagination state')
        return current
