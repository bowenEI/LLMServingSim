// Keep the English and Chinese documentation trees structurally identical.
// Matching relative paths make the language switcher predictable for every
// document page and prevent one language from silently losing a page.

import {readdirSync, statSync} from 'node:fs';
import {join, relative, resolve} from 'node:path';

const docsRoot = resolve(new URL('..', import.meta.url).pathname, 'docs');

function filesUnder(root) {
  const files = [];
  function walk(dir) {
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) walk(path);
      else if (statSync(path).isFile()) files.push(relative(root, path));
    }
  }
  walk(root);
  return new Set(files.sort());
}

const english = filesUnder(join(docsRoot, 'en'));
const chinese = filesUnder(join(docsRoot, 'zh'));
const englishOnly = [...english].filter((path) => !chinese.has(path));
const chineseOnly = [...chinese].filter((path) => !english.has(path));

if (englishOnly.length || chineseOnly.length) {
  if (englishOnly.length) {
    console.error('English-only documentation files:');
    for (const path of englishOnly) console.error(`  ${path}`);
  }
  if (chineseOnly.length) {
    console.error('Chinese-only documentation files:');
    for (const path of chineseOnly) console.error(`  ${path}`);
  }
  process.exit(1);
}

console.log(`documentation trees match (${english.size} files)`);
