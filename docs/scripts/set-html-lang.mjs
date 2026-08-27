// Separate content plugins share Docusaurus' default `en` site locale, so
// Chinese plugin pages would otherwise be emitted with <html lang="en">.
// Set the static language attribute from the public route after the build;
// src/theme/Root.tsx keeps it correct during client-side navigation as well.

import {readFileSync, readdirSync, writeFileSync} from 'node:fs';
import {join, resolve} from 'node:path';

const buildDir = resolve(new URL('..', import.meta.url).pathname, 'build');

function walk(dir) {
  for (const entry of readdirSync(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) walk(path);
    else if (entry.name.endsWith('.html')) {
      const language = path.startsWith(join(buildDir, 'zh')) ? 'zh-CN' : 'en';
      const html = readFileSync(path, 'utf8');
      const updated = html.replace(/<html\s+lang=[^ >]+/, `<html lang=${language}`);
      if (updated !== html) writeFileSync(path, updated);
    }
  }
}

walk(buildDir);
