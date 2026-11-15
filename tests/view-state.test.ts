import test from 'node:test';
import assert from 'node:assert/strict';
import {readView,viewQuery} from '../src/viewState.ts';

test('comparison URL round-trips the actual frames and each display choice',()=>{
  const view=readView('?compare=swipe&frame_a=2&frame_b=0&independent=1&stretch_a=.7&stretch_b=2&divider=30&zoom=1.25&x=-20',3);
  assert.deepEqual(view.comparison,{enabled:true,mode:'swipe',frame_a:2,frame_b:0,independent:true,stretch_a:.7,stretch_b:2,divider:30});
  assert.deepEqual(readView('?'+viewQuery(view),3),view);
});

test('comparison controls clamp invalid values and reject unavailable/single-frame modes',()=>{
  const value=readView('?compare=swipe&frame_a=999&frame_b=-20&stretch_a=Infinity&stretch_b=99&divider=NaN',2).comparison;
  assert.deepEqual(value,{enabled:true,mode:'swipe',frame_a:1,frame_b:0,independent:false,stretch_a:1,stretch_b:3,divider:50});
  assert.equal(readView('?compare=unknown',3).comparison.enabled,false);
  assert.equal(readView('?compare=swipe',1).comparison.enabled,false);
  assert.equal(readView('?compare=swipe',1).comparison.frame_b,0);
  assert.equal(readView('',3).comparison.enabled,false);
});
