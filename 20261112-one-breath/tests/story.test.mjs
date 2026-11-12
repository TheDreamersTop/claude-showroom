// The epitaph shown after a pop states numbers as fact, so the numbers must be right.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hairFraction, epitaph } from '../js/story.js';

test('thickness is compared with a 70 micron hair, rounded to two significant figures', () => {
  assert.equal(hairFraction(9), '1/7,800');
  assert.equal(hairFraction(70), '1/1,000');
  assert.equal(hairFraction(700), '1/100');
});

test('epitaph reports whole seconds lived and whole nanometres at the thinnest spot', () => {
  const e = epitaph({ ageS: 52.6, thinnestNm: 9.4 });
  assert.match(e.en, /Lived 53 s\./);
  assert.match(e.en, /9 nm/);
  assert.match(e.en, /1\/7,400 of a hair/);
  assert.match(e.zh, /53 秒/);
});

test('a bubble poked before it thinned still gets an honest epitaph', () => {
  const e = epitaph({ ageS: 3.2, thinnestNm: 640 });
  assert.match(e.en, /Lived 3 s\./);
  assert.match(e.en, /640 nm/);
});

test('a bubble popped before any thickness was measured never prints Infinity or NaN', () => {
  const e = epitaph({ ageS: 0.2, thinnestNm: Infinity });
  assert.doesNotMatch(e.en + e.zh, /Infinity|NaN/);
  assert.match(e.en, /Lived 0 s\./);
});

test('the epitaph says how big the breath made the bubble, so a long breath and a quick puff end differently', () => {
  const big = epitaph({ ageS: 45, thinnestNm: 12, diameterCm: 8 });
  const small = epitaph({ ageS: 70, thinnestNm: 12, diameterCm: 4 });
  assert.match(big.en, /8 cm across/);
  assert.match(small.en, /4 cm across/);
  assert.match(big.zh, /8 公分/);
});
