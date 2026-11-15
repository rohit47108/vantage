import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {selectTemporalFrames,temporalDayGroups,parseTimeSelection} from '../src/timeSelection.ts';
import {readView,viewQuery} from '../src/viewState.ts';

const catalog=JSON.parse(readFileSync('public/prepared/catalog.json','utf8'));
const empty={start_date:'',end_date:'',group_date:''};

test('real UTC-day groups retain Ceres exposures and their actual midpoint interval',()=>{
  const frames=catalog.find((s:any)=>s.key==='ceres').frames,groups=temporalDayGroups(frames,empty);
  assert.equal(groups.length,1);assert.equal(groups[0].day,'2025-07-03');assert.deepEqual(groups[0].indices,[0,1]);
  assert.equal(groups[0].first_midpoint,frames[0].utc_mid);assert.equal(groups[0].last_midpoint,frames[1].utc_mid);
  assert.deepEqual(selectTemporalFrames(frames,{...empty,group_date:groups[0].day}),[0,1]);
});

test('inclusive UTC midpoint dates preserve original indices and explicit empty selections',()=>{
  const frames=catalog.find((s:any)=>s.key==='wise0855').frames,selection={...empty,start_date:'2026-04-30',end_date:'2026-05-08'};
  assert.deepEqual(selectTemporalFrames(frames,selection),[1,2]);
  assert.deepEqual(selectTemporalFrames(frames,{...selection,group_date:'2026-05-08'}),[2]);
  assert.deepEqual(selectTemporalFrames(frames,{...empty,start_date:'2026-06-01'}),[]);
  assert.deepEqual(selectTemporalFrames(frames,{...empty,start_date:'2026-05-08',end_date:'2026-04-30'}),[]);
  assert.deepEqual(selectTemporalFrames([{utc_mid:'2026-01-01T00:10:00+02:00'}],{...empty,end_date:'2025-12-31'}),[0]);
});

test('calendar validation and saved temporal selection round-trip without fabricating groups',()=>{
  assert.deepEqual(parseTimeSelection(new URLSearchParams('time_start=2026-02-31&time_end=bad&time_day=2026-07-03')), {...empty,group_date:'2026-07-03'});
  const view=readView('?time_start=2026-04-30&time_end=2026-05-08&time_day=2026-05-08&frame=2',3);
  assert.deepEqual(view.time_selection,{start_date:'2026-04-30',end_date:'2026-05-08',group_date:'2026-05-08'});
  assert.deepEqual(readView('?'+viewQuery(view),3),view);
});
