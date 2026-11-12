// Physics checks for the soap film. Each test names the real-world fact it protects,
// because a bubble that shows the wrong colour for its thickness is a lie the page tells.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filmRGB, rimSpeed } from '../js/film.js';

const sum = (c) => c[0] + c[1] + c[2];

test('a film thinner than light is black (Newton black film, seen just before a bubble pops)', () => {
  assert.ok(sum(filmRGB(0, 1)) < 0.003, `got ${filmRGB(0, 1)}`);
  assert.ok(sum(filmRGB(8, 1)) < 0.02);
});

test('around 100 nm the film looks silvery white: bright and nearly colourless', () => {
  const c = filmRGB(100, 1);
  assert.ok(sum(c) > 20 * sum(filmRGB(8, 1)));
  assert.ok(Math.max(...c) / Math.min(...c) < 1.3, `got ${c}`);
});

test('magenta near 200 nm, where the first order ends: green cancels, red and blue survive', () => {
  const [r, g, b] = filmRGB(205, 1);
  assert.ok(r > g && b > g, `got ${[r, g, b]}`);
});

test('second-order blue near 250 nm', () => {
  const [r, g, b] = filmRGB(250, 1);
  assert.ok(b > r && b > g, `got ${[r, g, b]}`);
});

test('second-order yellow near 340 nm', () => {
  const [r, g, b] = filmRGB(340, 1);
  assert.ok(r > b && g > b, `got ${[r, g, b]}`);
});

test('a thick film (5 microns) washes out to a colourless grey', () => {
  const c = filmRGB(5000, 1);
  const m = sum(c) / 3;
  for (const x of c) assert.ok(Math.abs(x - m) / m < 0.15, `got ${c}`);
});

test('tilting the view shifts the colour: the same film is not the same colour at the rim', () => {
  const a = filmRGB(250, 1), b = filmRGB(250, 0.3);
  assert.ok(Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]) > 0.02);
});

test('Taylor-Culick: a hole in a 1 micron film opens at about 7 m/s', () => {
  assert.ok(Math.abs(rimSpeed(1000) - 7.07) < 0.05, `got ${rimSpeed(1000)}`);
});

test('Taylor-Culick: thinner film retracts faster (speed grows as 1/sqrt(h))', () => {
  assert.ok(Math.abs(rimSpeed(250) / rimSpeed(1000) - 2) < 1e-9);
});
