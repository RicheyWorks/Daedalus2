# PythonScriptCommandlet flag parsing in UE 5.8.3 (read-only source check)

Owner: unreal-epic-boss. Item c of buffffff 48347/48367 (request_id buf-ueb-p1-epic-scrapes-20261019); answers PootScoot 48184 ("commandlet flags not verified; read actual parse before future packet").
Method: read the installed engine source on BLACKBEARD only. Nothing was compiled, launched or run. No commandlet has been executed, so every "runtime" statement below is UNVERIFIED until a second-process custody window exists.

## Sources read (installed `C:\Program Files\Epic Games\UE_5.8\Engine`)

| File | SHA-256 |
|---|---|
| `Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PythonScriptCommandlet.cpp` (78 lines) | `068f6468b9fc37652b00c393d3e113ebb7a3a02f6b95240089006e61c58f17d0` |
| `Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PythonScriptPlugin.cpp` | `73dcc53c2ee5af97e36f87fa62de1181f876a0c29ae82bdc592b3d793242c205` |
| `Source/Runtime/Core/Private/Misc/Parse.cpp` | `31aa20d52c7a54ab3464ba1c79f6087ee18c28b9ba312c481804521de538690c` |
| `Source/Runtime/Launch/Private/LaunchEngineLoop.cpp` | `c45991a136185130235e507c9bb9ec6e926d4f2006a384b2f61e7e6227742c6f` |
| `Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Public/PythonScriptTypes.h` | (defaults only, lines 72-81) |

## What the code does

1. **Which string the commandlet sees.** `LaunchEngineLoop.cpp` (around line 2233) builds `CommandletCommandLine = FString::Join(QuotedTokenArray, " ")`, i.e. the WHOLE process command line re-joined from `TokenizeCommandline(CmdLine, true)` tokens, and passes it to `UPythonScriptCommandlet::Main(Params)` (line 4110). So `Params` also holds the project path, `-run=pythonscript` and every other switch.
2. **`-Script=` is found by substring, not by `FParse::Value`.** `Main` does `Params.Find(TEXT("-Script="))` (comment: done manually because scripts "may be quoted and contain escape sequences that the command line parsing doesn't handle well"). `FString::Find` defaults to case-insensitive, so the FIRST `-script=` anywhere in the line wins, including one inside an earlier argument's value.
3. **Quoted value: `FParse::QuotedString`** (when the character after `=` is `"`). It reads to the next unescaped `"` and DOES process C-style escapes: `\\` `\"` `\'` `\n` `\r` `\t`, octal `\NNN`, `\xHH..`, `\uHHHH`, `\UHHHHHHHH`. Any other `\c` is kept as two characters. A newline or CR ends the value. A missing closing quote makes the parse fail, so the commandlet logs `-Script argument not specified` and returns -1.
   - **Pitfall:** a quoted Windows path is altered silently. `"C:\Users\730ri\projects\bot-team\native\test.py"` turns `\n` into a newline, `\t` into a tab and `\b` stays literal. Paths such as `...\native-ingestion\...`, `...\tools\...` or `...\task-2\...` break. **Use forward slashes (or doubled backslashes) inside a quoted `-Script=`.**
4. **Unquoted value: `FParse::Token(..., bUseEscape=false)`.** It stops at the first whitespace, and an embedded `"..."` part is kept with its quotes. Backslashes are untouched, so `-Script=C:\path\check.py` (no spaces) is safe, but it cannot carry arguments.
5. **File vs literal code.** `FPythonCommandEx` defaults to `ExecutionMode = ExecuteFile` and `FileExecutionScope = Private`, and the commandlet adds `EPythonCommandFlags::Unattended`. `ExecPythonCommandEx` searches the script string for the first `.py`:
   - If found (and followed by end, whitespace, or a closing quote when the path started with `"`), it is run as a FILE via `RunFile`. Everything after it becomes arguments.
   - Otherwise the whole string runs as LITERAL Python (`RunString`). `C:\x\check.py-t` (no space) silently falls back to running the text as code. A `.py` anywhere in literal code (e.g. `print("a.py")`) makes it try to treat the prefix as a path.
   - A bare name like `check.py` is looked up on `sys.path`.
6. **`sys.argv`.** The plugin uses `FPythonScopedArgv`, which tokenizes the args with `FParse::Token(InArgs, Token, false)`: whitespace-separated, a leading `"` starts a quoted token, and no escapes are processed at this stage. On Python >= 3.11 it sets `sys.argv` directly, and `argv[0]` is the re-quoted script path. argv is reset after the run.
7. **Exit code.** `Main` returns 0 on success and -1 when `-Script` is missing/empty, Python is unavailable, or `ExecPythonCommandEx` returns false. The `ErrorLevel` from `Main` becomes the process result (line 4110). UNVERIFIED: whether an uncaught Python exception in a file always maps to `false` (inspect `RunFile` and the log line `Python script executed with errors` on a real run).
8. **Before the script runs:** `ForceEnablePythonAtRuntime()`, then `RunStartupScripts()` (project `init_unreal.py`/startup scripts run first in the commandlet process too), then an `FScopedSourceControl` scope.

## Safe invocation pattern (proposal, NOT run)

```
UnrealEditor-Cmd.exe "C:/Unreal/DaedalusRealm/DaedalusRealm.uproject" -run=pythonscript -Script="C:/path/with/forward/slashes/check.py --out C:/tmp/result.json" -unattended -nosplash -stdout
```

Rules for any future packet:
- Put `-Script=` LAST and make sure no earlier argument contains the text `-script=`.
- Forward slashes inside the quotes. No `\n`, `\t` or `\x` sequences.
- Exactly one ` ` (space) between `.py` and the first argument.
- The script writes its own JSON result file. Do not rely on stdout or on exit code alone; check the result file and the `LogPythonScriptCommandlet` lines `Running Python script:` / `executed successfully`.
- UNVERIFIED and not covered here: the extra switches (`-unattended`, `-nosplash`, `-stdout`, `-nullrhi`, `-FullStdOutLogOutput`) and how `TokenizeCommandline(CmdLine, true)` re-quotes tokens that contain spaces. Check those in a later read before relying on them.

## Custody constraint

A commandlet is a second UnrealEditor process loading the same project. Under the current one-writer rule (PID 23632 live, sole operator unreal-epic-boss to 16:23 UTC), it must not run against `C:\Unreal\DaedalusRealm` while 23632 is open. It needs a separate custody window or an isolated project copy, plus its own RAM guard (current floor: 1.0 GB physical free and 4 GB commit free, per Richey 01:46 PT). This is also why the fresh-process reopen step stays PENDING for imports in this window.