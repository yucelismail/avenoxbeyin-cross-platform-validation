"""Neutral receipt contract plus observed effects of status policy."""
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'semantic'))
import contract_test
subject=contract_test.subject
OBSERVATIONS=[]

class CommonReceiptContract(contract_test.ReceiptContract):
    def check_preserved(self, incoming):
        self.assertEqual(self.path.read_bytes(),incoming)
        with self.engine.store._connect() as db:
            self.assertEqual(db.execute('SELECT payload FROM receipts WHERE id=?',(self.metadata['event_id'],)).fetchone()[0],self.stored)

    def record(self, **data):
        OBSERVATIONS.append(dict(test=self.id().split('.')[-1], **data))

    def assert_divergence(self, incoming):
        for repeat in (1,2):
            report=self.engine.sync()
            notices=report['warnings']+report['conflicts']
            self.record(repeat=repeat, report=report)
            self.assertIn(report['status'],('degraded','conflict'))
            self.assertTrue(any(n.get('source')==self.source for n in notices),report)
            self.check_preserved(incoming)
        staging=self.path.with_suffix('.restore');staging.write_bytes(self.original);os.replace(staging,self.path)
        report=self.engine.sync();self.record(restored=report)
        self.assertEqual(report['status'],'succeeded');self.check_preserved(self.original)

    def check_conflict(self,field,value):
        self.assert_divergence(self.replace(field,value))

    def check_metadata(self,field,value):
        incoming=self.replace(field,value)
        for repeat in (1,2):
            report=self.engine.sync();self.record(repeat=repeat,report=report)
            self.assertEqual(report['status'],'succeeded')
            self.assertFalse(any(n.get('source')==self.source for n in report['warnings']+report['conflicts']))
        self.check_preserved(incoming)

    def custom_replace(self, metadata, body):
        incoming=subject.render(metadata,body).encode();stage=self.path.with_suffix('.incoming');stage.write_bytes(incoming);os.replace(stage,self.path)
        os.utime(self.path.parent,(1700000001,1700000001))
        return incoming

    def test_both_semantic_fields(self):
        metadata=dict(self.metadata,refs=['notes/other.md'])
        self.assert_divergence(self.custom_replace(metadata,'Different summary\n'))

    def test_metadata_combined(self):
        incoming=self.custom_replace(dict(self.metadata,created_at='2026-10-05T12:00:00+00:00',session='other',harness='codex'),self.body)
        report=self.engine.sync();self.record(report=report)
        self.assertEqual(report['status'],'succeeded');self.check_preserved(incoming)

    def test_metadata_and_summary(self):
        incoming=self.custom_replace(dict(self.metadata,harness='codex',session='other'),'Different summary\n')
        self.assert_divergence(incoming)

    def test_refs_order(self):
        result=self.engine.receipt('ordered-event','Original summary',['notes/source.md','notes/other.md'],'manual')
        self.source=result['source'];self.path=self.vault/self.source;self.original=self.path.read_bytes()
        self.metadata,self.body=subject.parse(self.original.decode())
        with self.engine.store._connect() as db:
            self.stored=db.execute('SELECT payload FROM receipts WHERE id=?',('ordered-event',)).fetchone()[0]
        self.assert_divergence(self.replace('refs',['notes/other.md','notes/source.md']))

    def test_invalid_metadata_is_warning(self):
        incoming=self.replace('created_at','not-a-date')
        report=self.engine.sync();self.record(report=report)
        self.assertEqual(report['status'],'degraded');self.check_preserved(incoming)
        self.assertTrue(any(w.get('source')==self.source for w in report['warnings']))

    def capture_call(self, call):
        try: return {'result':call(),'error':None}
        except (subject.ReceiptConflict,subject.RevisionConflict) as exc:
            return {'result':None,'error':type(exc).__name__,'message':str(exc)}

    def test_unrelated_receipt_effect(self):
        incoming=self.replace('summary','Different summary\n')
        observed=self.capture_call(lambda:self.engine.receipt('independent-event','Independent receipt',['notes/other.md'],'manual'))
        with self.engine.store._connect() as db:
            observed['independent_db_row_exists']=bool(db.execute('SELECT 1 FROM receipts WHERE id=?',('independent-event',)).fetchone())
        observed['independent_file_exists']=(self.vault/('receipts/'+subject._hash('independent-event')+'.md')).is_file()
        self.check_preserved(incoming);self.record(**observed)

    def test_task_update_effect(self):
        self.engine.task_create('tasks/independent.md','Synthetic task.',{'id':'independent-task','kind':'task','revision':1,'status':'active','owner':'Synthetic Reviewer'})
        incoming=self.replace('summary','Different summary')
        observed=self.capture_call(lambda:self.engine.update_task('independent-task',1,{'status':'waiting'}))
        meta,_=subject.parse((self.vault/'tasks/independent.md').read_text(encoding='utf-8'))
        with self.engine.store._connect() as db:
            row=json.loads(db.execute('SELECT payload FROM records WHERE id=?',('independent-task',)).fetchone()[0])
        observed.update(file_revision=meta['revision'],file_status=meta['status'],db_revision=row['revision'],db_status=row['status'])
        self.check_preserved(incoming);self.record(**observed)

    def test_hook_ack_effect(self):
        import beyin_v3_hook as hook
        incoming=self.replace('summary','Different summary')
        state=self.engine.state
        hook.enqueue_event(self.vault,state,{'hook_event_name':'SessionEnd','session_id':'synthetic-session','event_id':'synthetic-hook-event'},'codex')
        first=hook.drain_queue(self.vault,state);second=hook.drain_queue(self.vault,state)
        health=json.loads((state/'hook-health.json').read_text(encoding='utf-8'))
        self.record(first=first,second=second,health=health,
                    pending=len(list((state/'hook-queue').glob('*.json'))),done=len(list((state/'hook-done').glob('*.json'))))
        self.check_preserved(incoming)

    def test_reassert_metadata_write_api(self):
        incoming=self.replace('session','other')
        observed=self.capture_call(lambda:self.engine.receipt('synthetic-event','Original summary',['notes/source.md'],'manual',session='original'))
        self.assertEqual(observed['error'],'ReceiptConflict');self.check_preserved(incoming);self.record(**observed)

suite=unittest.defaultTestLoader.loadTestsFromTestCase(CommonReceiptContract)
result=unittest.TestResult();suite.run(result)
print(json.dumps({'tests':result.testsRun,'failures':[t.id().split('.')[-1] for t,_ in result.failures],
 'errors':[t.id().split('.')[-1] for t,_ in result.errors], 'details':[s for _,s in result.failures+result.errors],
 'observations':OBSERVATIONS},ensure_ascii=False))
raise SystemExit(2 if result.errors else 1 if result.failures else 0)
