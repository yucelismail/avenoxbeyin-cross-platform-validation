#!/usr/bin/env python3
"""Pinned main/ours/peer comparison. No status preference in shared acceptance."""
import argparse
from datetime import datetime,timezone
import hashlib,json,os,platform,subprocess,sys,tempfile,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE='9b9aa95848b7dbee6ba13415c3615671d4445862'
PEER='13ea7258a602009380c20cc2e591a51e65641617'
SOURCE=Path('template/.claude/scripts/beyin_v3_sync.py')
TARGETS={'full_payload_compare':{'test_created_at_metadata','test_session_metadata','test_harness_metadata'},
         'skip_existing_receipts':{'test_summary_conflict','test_refs_conflict'},
         'always_succeeded':{'test_summary_conflict','test_refs_conflict'}}


def command(cmd,**kw):
    return subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=kw.pop('timeout',120),**kw)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--main-checkout',type=Path);parser.add_argument('--peer-checkout',type=Path)
    args=parser.parse_args()
    output=ROOT/('receipt-comparison-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));output.mkdir()
    report={'platform':platform.platform(),'python':platform.python_version(),'base_sha':BASE,'peer_sha':PEER,'status':'setup_failed','common':[],'strict':[],'product':{}}
    code=2
    try:
        with tempfile.TemporaryDirectory(prefix='receipt-policy-') as td:
            paths={}
            for name,sha,url in [('main',BASE,'https://github.com/avenoxai/avenoxbeyin.git'),('peer',PEER,'https://github.com/hknsahin97-coder/avenoxbeyin.git')]:
                supplied=getattr(args,name+'_checkout');path=supplied.resolve() if supplied else Path(td)/name
                if not supplied:
                    for cmd in (['git','init',str(path)],['git','-C',str(path),'fetch','--depth=1',url,sha],['git','-C',str(path),'checkout','--detach','FETCH_HEAD']): command(cmd).check_returncode()
                if command(['git','-C',str(path),'rev-parse','HEAD']).stdout.strip()!=sha:raise ValueError('candidate SHA mismatch')
                command(['git','-C',str(path),'diff','--quiet','HEAD','--','template/.claude/scripts','tests']).check_returncode()
                paths[name]=path
            ours=Path(td)/'ours';command(['git','clone','--no-hardlinks',str(paths['main']),str(ours)]).check_returncode()
            patch=ROOT/'sync/semantic/main-semantic.patch';report['patch_sha256']=hashlib.sha256(patch.read_bytes()).hexdigest()
            if report['patch_sha256']!=patch.with_suffix('.patch.sha256').read_text().strip():raise ValueError('patch hash mismatch')
            command(['git','-C',str(ours),'apply','--check',str(patch)]).check_returncode()
            command(['git','-C',str(ours),'apply',str(patch)]).check_returncode()
            regression=(ROOT/'sync/semantic/contract_test.py').read_text().replace("Path(os.environ['SYNC_CANDIDATE'])","Path(os.environ.get('SYNC_CANDIDATE',str(Path(__file__).resolve().parents[1])))")
            (ours/'tests/v3_receipt_semantic_test.py').write_text(regression,encoding='utf-8',newline='')
            paths['ours']=ours
            original=(ours/SOURCE).read_text()
            for name in TARGETS:
                target=Path(td)/name;command(['git','clone','--no-hardlinks',str(paths['main']),str(target)]).check_returncode()
                old,new=({
                  'full_payload_compare':("if previous[field] != event[field]]","if previous != event]"),
                  'skip_existing_receipts':("                if row:\n                    previous = json.loads(row[0])","                if row:\n                    continue\n                    previous = json.loads(row[0])"),
                  'always_succeeded':("'status': 'conflict' if conflicts else 'degraded' if warnings else 'succeeded'","'status': 'succeeded'")})[name]
                if original.count(old)!=1:raise ValueError('mutant anchor mismatch')
                mutated=original.replace(old,new,1);compile(mutated,'<mutant>','exec');(target/SOURCE).write_text(mutated,encoding='utf-8',newline='');paths[name]=target
            report['sources']={name:hashlib.sha256((path/SOURCE).read_bytes()).hexdigest() for name,path in paths.items()}
            for name,path in paths.items():
                for repeat in (1,2):
                    proc=command([sys.executable,str(ROOT/'sync/comparison/policy_probe.py')],env=dict(os.environ,SYNC_CANDIDATE=str(path),PYTHONIOENCODING='utf-8'))
                    data=json.loads(proc.stdout);data.update(candidate=name,repeat=repeat,exit=proc.returncode);report['common'].append(data)
            for name in ('ours','peer'):
                proc=command([sys.executable,str(ROOT/'sync/semantic/run_suite.py')],env=dict(os.environ,SYNC_CANDIDATE=str(paths[name]),PYTHONIOENCODING='utf-8'))
                data=json.loads(proc.stdout);data.update(candidate=name,exit=proc.returncode);report['strict'].append(data)
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',BEYIN_V3_NO_SPAWN='1')
                env.pop('SYNC_CANDIDATE',None)
                proc=command([sys.executable,'-m','unittest','discover','-s','tests','-p','v3_*test.py'],cwd=paths[name],env=env,timeout=900)
                text=proc.stdout+proc.stderr
                (output/(name+'-full-v3.log')).write_text(text,encoding='utf-8')
                report['product'][name]={'exit':proc.returncode}
                proc=command([sys.executable,str(paths[name]/'scripts/evaluate_v3.py')],env=env)
                (output/(name+'-retrieval.json')).write_text(proc.stdout,encoding='utf-8');(output/(name+'-retrieval.stderr')).write_text(proc.stderr,encoding='utf-8')
                report['product'][name]['retrieval_exit']=proc.returncode
            complete=len(report['common'])==12 and all(r['tests']==17 and not r['errors'] and r['exit'] in (0,1) for r in report['common'])
            positive=all(r['exit']==0 for r in report['common'] if r['candidate'] in ('ours','peer'))
            kills={name:all(r['exit']==1 and targets.issubset(r['failures']) for r in report['common'] if r['candidate']==name) for name,targets in TARGETS.items()}
            report['mutant_kills']=kills
            products=all(v['exit']==0 and v['retrieval_exit']==0 for v in report['product'].values())
            report['status']='passed' if complete and positive and all(kills.values()) and products else 'failed'
            code=0 if report['status']=='passed' else 1 if complete else 2
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)
    (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Receipt policy comparison','',f"Status: **{report['status']}**",'', '| Candidate | Repeat | Tests | Failures | Errors |','| --- | ---: | ---: | --- | --- |']
    for r in report['common']:lines.append(f"| {r['candidate']} | {r['repeat']} | {r['tests']} | {', '.join(r['failures']) or 'none'} | {', '.join(r['errors']) or 'none'} |")
    lines+=['','Shared tests accept either degraded/warnings or conflict/conflicts when source visibility and preservation hold. Strict schema mismatches are reported separately and are not product failures. Three effect scenarios record behavior without declaring one status policy correct.','',f"Product results: `{json.dumps(report['product'])}`"]
    text='\n'.join(lines)+'\n';(output/'REPORT.md').write_text(text,encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:f.write(text)
    with zipfile.ZipFile(output.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in output.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(output))
    print(report['status'],output.name);return code

if __name__=='__main__':raise SystemExit(main())
