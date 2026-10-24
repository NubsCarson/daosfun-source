# Reproduce the exact binary

The root workspace is the recovered source. Build with the pinned compiler and Cargo.lock, then use the recovered linker ordering. A normal `anchor build` does not apply this ordering and is not the byte-identical recipe.

This reconstruction produces the original program's bytes. It does not establish a unique historical lockfile, original variable names, or original compiler flags. The explicit section order is a recovered part of this recipe. No original instruction or data bytes are injected into compilation or linking.

## Linux prerequisites

Use x86-64 Linux with Python 3.12, a C toolchain, OpenSSL development headers, and network access for the first setup. On Ubuntu 24.04:

```sh
sudo apt-get update
sudo apt-get install -y python3 build-essential pkg-config libssl-dev
python3 scripts/setup_repro.py
python3 scripts/build_exact.py
```

Setup downloads the [official Anza platform-tools v1.41 release](https://github.com/anza-xyz/platform-tools/releases/tag/v1.41) and the 264 registry packages listed in `Cargo.lock` from `static.crates.io`. Every crate archive is checked against Cargo.lock's SHA-256; all 47 recorded compiler/runtime components are checked against `repro/toolchain-components.json`. Setup does not execute crate build scripts. Downloads and vendor trees are excluded from Git.

The compiler is the official Linux x86-64 `rustc 1.75.0-dev` with LLVM 17.0.6. The SBF target is `sbf-solana-solana`. Anchor is 0.30.1 and `solana-program` is 1.18.26. The workspace release profile enables overflow checks, disables LTO, and uses one codegen unit. The complete dependency set is in Cargo.lock.

The build runs Cargo **offline and locked** with an initially absent target cache. It captures the newly compiled objects, applies `repro/order-mapping.json` and `repro/constant-order.json`, strips with the official LLVM tool, and compares the result with `evidence/mainnet.so`. The original is only an input to verification.

## Outputs and expected hashes

The default output is `.build/exact/`:

| File | Meaning |
| --- | --- |
| `linked/dao_v1.deployed.so` | ELF plus 79,056 newly generated zero bytes; exactly matches the entire 1,120,784-byte captured account payload |
| `verification.json` | Whole-file equality and SHA-256 results |
| `source-manifest.json` | Hashes of source/configuration inputs |
| `toolchain-verification.json` | Verified compiler/runtime hashes |
| `build.log`, `command.json` | Compiler output and invocation |
| `capture/`, `linked/link.map` | Fresh linker inputs, hashes, script, and layout evidence |

The linker uses an unpadded ELF internally. It is not a separately published comparison artifact. The ELF portion of the padded output has SHA-256:

```text
145716b96a30edc81413a77caea1c06c8aaf6adf3ad65b1576d6b9469f226e07
```

Expected full captured-file SHA-256:

```text
5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d
```

`build_exact.py` refuses existing output or target directories. Repeat with a fresh name:

```sh
python3 scripts/build_exact.py --output .build/repeat-2
```

Do not reformat the recovered Rust source: panic line/column records are part of the executable. The checked-in binaries are comparison artifacts, not patched versions or deployment instructions.

## Existing compiler or vendor directories

```sh
python3 scripts/build_exact.py \
  --toolchain /absolute/path/to/platform-tools-v1.41 \
  --vendor /absolute/path/to/vendor \
  --output .build/existing-tools
```

`TOOLCHAIN`, `VENDOR`, and `TARGET` environment variables supply the corresponding defaults. `--jobs` defaults to 4. Native Linux generally uses the system host linker. Cross-host emulation may require `CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER` and `LD_LIBRARY_PATH` for the host compiler; these are environment-specific, not changes to the SBF source.

## Hosted reproduction

Run the **Rebuild exact source** workflow manually through GitHub Actions. It provisions the compiler and dependencies, performs an independent clean build on Ubuntu 24.04, and uploads its build log and verification evidence. A workflow definition alone is not evidence of a successful hosted run; consult the actual run result.

## Validation record

Both independent reproduction checks passed on 2026-10-24:

- A clean build from the relocated repository under Linux x86-64 emulation reproduced both exact hashes, using the previously verified vendor tree. Compilation took 5 minutes 19 seconds.
- A [native Ubuntu 24.04 GitHub Actions build](https://github.com/lalalune/daosfun-source/actions/runs/40084472477) at commit `9b654c4e94cbb92ac88ac6268431ab780964161c` downloaded the official compiler and all pinned crates from scratch, built with an empty target cache, and reproduced both exact hashes. Its downloaded ELF and account-padded binary were independently compared with the repository reference files. Its source manifest matched the repository. See [hosted rebuild evidence](../repro/hosted-rebuild.json).

The separate local build using the freshly downloaded vendor tree was stopped once the native hosted build established that same check; it is not recorded as a completed local build. No further reproduction check remains pending.

Bootstrap of all 264 crates passed: all 12,102 vendored files matched the prior independently hashed recovery inputs. A fresh local download of the official compiler also passed all 47 recorded component checks. The build script clears ambient Rust flags and compiler wrappers and explicitly selects the verified compiler. [The portable validation receipt](../repro/portable-build-verification.json) records these outcomes.
