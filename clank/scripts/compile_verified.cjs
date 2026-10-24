#!/usr/bin/env node
'use strict';
// Compile a saved Sourcify Standard JSON input; do not import remote code or use chain calls.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const [recordPath, compilerPath, outputPath, requestedContract] = process.argv.slice(2);
if (!recordPath || !compilerPath || !outputPath) {
  throw new Error('Usage: node compile_verified.cjs SOURCIFY_JSON SOLJSON_JS OUTPUT_JSON [SOURCE:CONTRACT]');
}
const record = JSON.parse(fs.readFileSync(recordPath, 'utf8'));
const compiler = require(path.resolve(compilerPath));
const version = compiler.cwrap('solidity_version', 'string', [])();
if (version.split('.Emscripten')[0] !== record.compilation.compilerVersion) {
  throw new Error(`Compiler mismatch: ${version} != ${record.compilation.compilerVersion}`);
}
const input = structuredClone(record.stdJsonInput);
const label = path.basename(recordPath).replace(/-sourcify\.json$/, '');
const clankRoot = path.resolve(path.dirname(recordPath), '../..');
const sourceRoot = path.join(clankRoot, 'verified', label, 'sources');
for (const [unit, sourceInput] of Object.entries(input.sources)) {
  const file = path.resolve(sourceRoot, unit);
  if (!file.startsWith(sourceRoot + path.sep)) throw new Error(`Unsafe source path: ${unit}`);
  const content = fs.readFileSync(file, 'utf8');
  if (content !== sourceInput.content) throw new Error(`Recovered source differs from archived input: ${unit}`);
  sourceInput.content = content;
}
const fullyQualifiedName = requestedContract || record.compilation.fullyQualifiedName;
const split = fullyQualifiedName.lastIndexOf(':');
if (split < 1) throw new Error('Expected SOURCE:CONTRACT');
const source = fullyQualifiedName.slice(0, split);
const name = fullyQualifiedName.slice(split + 1);
input.settings.outputSelection = {[source]: {'': ['ast'], [name]: ['abi', 'evm.bytecode', 'evm.deployedBytecode', 'metadata']}};
const compile = compiler.cwrap('solidity_compile', 'string', ['string', 'number', 'number']);
const output = JSON.parse(compile(JSON.stringify(input), 0, 0));
const errors = (output.errors || []).filter(e => e.severity === 'error');
if (errors.length) throw new Error(errors.map(e => e.formattedMessage).join('\n'));
const artifact = output.contracts?.[source]?.[name];
if (!artifact) throw new Error('Compiler did not produce the requested contract');
const immutableNames = {};
function scan(value) {
  if (!value || typeof value !== 'object') return;
  if (value.nodeType === 'VariableDeclaration' && value.mutability === 'immutable') immutableNames[value.id] = value.name;
  for (const child of Object.values(value)) scan(child);
}
scan(output.sources?.[source]?.ast);
fs.mkdirSync(path.dirname(outputPath), {recursive:true});
fs.writeFileSync(outputPath, JSON.stringify({compilerVersion:version,
  compilerSha256:crypto.createHash('sha256').update(fs.readFileSync(compilerPath)).digest('hex'),
  contract:fullyQualifiedName,
  inputSha256:crypto.createHash('sha256').update(JSON.stringify(input)).digest('hex'),
  artifact, immutableNames, warnings:output.errors || []}, null, 2) + '\n');
console.log(`Compiled ${fullyQualifiedName}: ${outputPath}`);
