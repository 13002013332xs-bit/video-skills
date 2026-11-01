import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

MODULE=Path(__file__).resolve().parents[1]/'scripts/ziniao_agent.py'
spec=importlib.util.spec_from_file_location('ziniao_agent',MODULE)
agent=importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

def reply(value, *, status='succeeded', error=None):
    result={'status':status,'output':{'content':[{'type':'text','text':json.dumps(value)}]}}
    if error:result['error']=error
    return subprocess.CompletedProcess([],0,json.dumps(result),'')

class AgentTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.calls=[]

    def client(self,responses):
        responses=iter(responses)
        def run(argv,**kwargs):
            self.calls.append(argv)
            value=next(responses)
            if isinstance(value,Exception):raise value
            return value
        return agent.AgentClient(browser_id='example-store',task_id='example-round',
                                 evidence_dir=self.root,runner=run)

    def arguments(self,index):
        argv=self.calls[index]
        return json.loads(argv[argv.index('--arguments-json')+1])

    def test_exact_required_observation_precedes_next_action(self):
        required={'action':'screenshot','params':{'purpose':'extract','pixel_source':'image','target':'current candidate','format':'jpeg','quality':90}}
        c=self.client([reply({'result':False,'required_verification_call':required}),reply({'observed':True}),reply({'result':12})])
        self.assertIs(c.evaluate('false'),False)
        self.assertEqual(c.evaluate('12'),12)
        self.assertEqual(self.arguments(1),required)
        self.assertTrue(all(a[0:3]==['zn-open-eco','agent','tool'] for a in self.calls))

    def test_auth_failure_without_status_is_not_pending_or_retried(self):
        r=subprocess.CompletedProcess([],1,json.dumps({'success':False,'error':{'code':'AUTH_SERVICE_UNAVAILABLE','message':'auth unavailable'}}),'')
        c=self.client([r])
        with self.assertRaises(agent.AgentError):c.evaluate('1')
        self.assertEqual(len(self.calls),1)
        self.assertFalse(list(self.root.glob('pending-*.json')))

    def test_actual_pending_receipt_is_saved_and_not_resubmitted(self):
        c=self.client([reply({},status='running')])
        with self.assertRaises(agent.PendingToolCall):c.evaluate('1')
        self.assertEqual(len(self.calls),1)
        receipt=json.loads(next(self.root.glob('pending-*.json')).read_text())
        self.assertEqual(receipt['status'],'running')
        self.assertTrue(receipt['tool_call_id'])

    def test_timeout_is_uncertain_and_never_blindly_replayed(self):
        c=self.client([subprocess.TimeoutExpired('example',20)])
        with self.assertRaises(agent.PendingToolCall):c.browser('click',{'ref':'example','expect_file_chooser':False,'download':False})
        self.assertEqual(len(self.calls),1)
        self.assertEqual(json.loads(next(self.root.glob('pending-*.json')).read_text())['status'],'unknown-after-timeout')

    def test_redacted_preview_cannot_be_used_as_complete_rows(self):
        c=self.client([reply({'result':{'parsed_json_preview':{'items':12,'preview':[1,2,3,4,5],'data_omitted':True},'original_chars':300,'data_omitted':True}})])
        with self.assertRaises(agent.IncompleteData):c.evaluate('observed rows')

    def test_verification_failure_does_not_repeat_business_click(self):
        required={'action':'snapshot','params':{'interactive':True,'maxChars':100000}}
        c=self.client([reply({'required_verification_call':required}),reply({},status='failed',error={'code':'snapshot_too_large','message':'too large'})])
        with self.assertRaises(agent.AgentError):c.browser('click',{'ref':'example','expect_file_chooser':False,'download':False})
        self.assertEqual([self.arguments(i)['action'] for i in range(2)],['click','snapshot'])

    def test_log_has_timing_but_not_message_or_image_content(self):
        c=self.client([reply({'result':'private reply'})])
        c.evaluate('private draft')
        text=(self.root/'agent-timing.jsonl').read_text()
        self.assertNotIn('private',text)
        self.assertIn('elapsed_seconds',text)

    def test_batches_require_all_expected_rows(self):
        rows=list(range(12));calls=[]
        def fetch(start,stop):calls.append((start,stop));return rows[start:stop]
        self.assertEqual(agent.read_batches(12,fetch),rows)
        self.assertEqual(calls,[(0,5),(5,10),(10,12)])
        with self.assertRaises(agent.IncompleteData):agent.read_batches(12,lambda a,b:[0])

    def test_no_progress_loop_is_bounded(self):
        p=agent.ProgressGuard(max_unchanged=2)
        p.observe(12,100)
        p.observe(12,200)
        p.observe(12,200)
        with self.assertRaises(agent.NoProgress):p.observe(12,200)
        p.observe(24,200)
        p.observe(24,200)

if __name__=='__main__':unittest.main()
