This file contains research performed by ChatGPT 5.6.

# Dictionary CLI Tools

## What matters most

Because you use both macOS and Debian, I would prioritize:

1. The same basic command on both machines.
2. Fast startup and readable terminal output.
3. Support for piping, scripting, and fuzzy spelling.
4. A reasonable path to offline lookup.
5. Dictionary data that is current enough for modern vocabulary.

The main distinction is **client versus dictionary source**. Tools such as `dict` and `sdcv` provide the interface, but
the quality and freshness of the definitions depend on the server or dictionary files behind them.

## 1. `dict`: the best conventional Unix option

`dict` is the standard command-line client for the DICT protocol. It is directly available through both Homebrew and
Debian, and supports selecting dictionaries, requesting spelling matches, listing available databases, and emitting
output intended for Unix post-processing. ([Debian Manpages][1])

Install it with:

```sh
# macOS
brew install dict

# Debian
sudo apt install dict
```

Try it without creating a configuration file:

```sh
dict -h dict.org serendipity
```

For persistent configuration, add this to `~/.dictrc`:

```text
server dict.org
```

Then your normal workflow becomes:

```sh
dict serendipity
dict -D                    # List available dictionary databases
dict -m serendippity       # Find approximate/spelling matches
dict -d DATABASE word      # Search one particular database
dict word | less -R
```

You could make it feel more natural with:

```sh
alias def='dict'
```

That gives you:

```sh
def perspicacious
```

### Why it is attractive

`dict` is simple, established, lightweight, and behaves like a traditional Unix program. It also returns useful exit
statuses—distinguishing successful lookups, approximate matches, connection failures, invalid databases, and other
cases—which makes it convenient in scripts. ([Debian Manpages][1])

Its weakness is the network protocol. DICT uses TCP port 2628, and queries and responses are normally sent unencrypted.
That means a public-server lookup should not be treated as private, and restrictive networks may block the connection.
([IETF Datatracker][2])

There is also a no-install diagnostic alternative using `curl`, which officially supports DICT URLs:

```sh
curl 'dict://dict.org/d:serendipity:*'
```

The output is less pleasant than the dedicated client, but it is useful for testing connectivity. ([Curl][3])

## 2. `sdcv`: the strongest offline option

`sdcv` is the console version of StarDict. It works entirely from local StarDict-format files and supports interactive
and noninteractive lookup, exact searches, fuzzy searches, full-text searches, wildcards, selecting specific
dictionaries, and JSON output. It is available through both Homebrew and Debian. ([Debian Manpages][4])

```sh
# macOS
brew install sdcv

# Debian
sudo apt install sdcv
```

Once dictionaries are installed:

```sh
sdcv serendipity
sdcv -e -n serendipity
sdcv -l
sdcv --json serendipity | jq
```

The flags in the second command mean:

- `-e`: exact search
- `-n`: noninteractive output

For an explicit, portable dictionary location:

```sh
export STARDICT_DATA_DIR="$HOME/.local/share/stardict"
mkdir -p "$STARDICT_DATA_DIR/dic"
```

Unpack StarDict dictionary files beneath:

```text
~/.local/share/stardict/dic/
```

Then place the environment variable in both your `.zshrc` and `.bashrc`, as appropriate.

### The important catch

Installing `sdcv` installs the engine, not a useful collection of definitions. You must obtain StarDict-format
dictionary data separately, and the resulting experience is only as good as those files.

FreeDict is a reputable source for open dictionary data and currently offers more than 140 dictionaries across roughly
45 languages. Its February 2026 update added StarDict support to 101 WikDict dictionaries. These are particularly useful
for bilingual lookup; finding an equally current, comprehensive, monolingual English StarDict dictionary can require
more hunting. ([FreeDict][5])

Once configured, however, `sdcv` is extremely fast, private, available without a connection, and more reliable than
depending on a public server.

## 3. An HTTPS API wrapped in a shell function

Because you are comfortable with shell tooling, a small `curl` and `jq` function is a competitive option. It gives you
HTTPS rather than the plaintext DICT protocol, and lets you control exactly how much information appears.

Install `jq` if needed:

```sh
# macOS
brew install jq

# Debian
sudo apt install jq
```

Then add this to your shell configuration:

```sh
define() {
  (($#)) || {
    printf 'usage: define WORD [WORD...]\n' >&2
    return 2
  }

  local query
  query=$(jq -rn --arg text "$*" '$text | @uri') || return

  curl -sS \
    "https://api.dictionaryapi.dev/api/v2/entries/en/$query" |
    jq -r '
      if type == "array" then
        .[] as $entry
        | (
            $entry.phonetic
            // $entry.phonetics[0].text
            // ""
          ) as $phonetic
        | (
            $entry.word
            + if $phonetic == ""
              then ""
              else "  " + $phonetic
              end
          ),
          (
            $entry.meanings[]
            | "\n[" + .partOfSpeech + "]",
              (
                .definitions[:3][]
                | "  - " + .definition
                  + if .example
                    then "\n    Example: " + .example
                    else ""
                    end
              )
          )
      else
        .message // "No definition found"
      end
    '
}
```

Usage:

```sh
define laconic
define "state of the art"
```

The Free Dictionary API exposes an English lookup endpoint, returns structured JSON, and uses Wiktionary as its
underlying source. ([Dictionary API][6])

This approach has some appealing qualities:

- Modern HTTPS transport.
- Easy control over output length and formatting.
- Definitions, parts of speech, phonetics, and examples.
- Straightforward integration into scripts or an `fzf` workflow.
- No dictionary dataset to maintain.

Its principal disadvantage is that you are depending on a community-run external service whose behavior or availability
could change. I would use it as a convenient personal lookup command, but not as a dependency in important automation.

For higher-quality editorial definitions, Merriam-Webster also offers an official API with definitions, etymologies,
pronunciations, synonyms, and antonyms. It requires registration and an API key; its free noncommercial allowance is
currently limited to 1,000 queries per day per key and two reference APIs. ([Merriam-Webster Dictionary][7])

## 4. WordNet: best for exploring relationships between words

The classic WordNet CLI is called `wn`:

```sh
# macOS
brew install wordnet

# Debian
sudo apt install wordnet
```

Basic lookup:

```sh
wn bank -over
```

WordNet becomes particularly useful when you want more than a definition:

```sh
wn bank -synsn    # Noun synonyms and immediate hypernyms
wn bank -hypen    # Noun hypernym tree
wn bank -hypon    # Noun hyponyms
wn good -antsa    # Adjective antonyms
```

The `wn` utility can show definitions—called glosses—along with synonyms, antonyms, hypernyms, hyponyms, derivational
relationships, domains, meronyms, holonyms, and other semantic links. ([WordNet][8])

WordNet is therefore excellent for writing, naming, taxonomy work, natural-language processing, or exploring how
concepts relate. It is less suitable as your only everyday dictionary because it does not focus on pronunciation,
etymology, contemporary slang, or richly edited usage examples.

The classic Homebrew `wordnet` formula is currently deprecated, although it remains installable. A more current route is
the Python `wn` package with Open English WordNet 2025+:

```sh
python3 -m venv ~/.local/venvs/wordnet
~/.local/venvs/wordnet/bin/pip install wn
~/.local/venvs/wordnet/bin/python -m wn download 'oewn:2025+'
```

The modern package provides up-to-date local WordNet data and a strong Python API, but its built-in CLI is primarily for
downloading and managing lexicons. You would need a small Python wrapper to turn it into a polished `define WORD`
command. ([WN Documentation][9])

## 5. macOS Dictionary Services: excellent, but Mac-only

macOS exposes the dictionaries enabled in Dictionary.app through its Dictionary Services framework. Apple’s
`DCSCopyTextDefinition` function searches the active dictionaries and returns the resulting definition. ([Apple
Developer][10])

You can turn it into a command by saving this as `~/.local/bin/macdef`:

```swift
#!/usr/bin/env swift

import Cocoa
import CoreServices.DictionaryServices

let term = CommandLine.arguments.dropFirst().joined(separator: " ")

guard !term.isEmpty else {
    print("usage: macdef WORD [WORD...]")
    exit(2)
}

let text = term as NSString
let range = CFRange(location: 0, length: text.length)

guard let result = DCSCopyTextDefinition(nil, text, range) else {
    print("No definition found for \"\(term)\"")
    exit(1)
}

print(result.takeRetainedValue())
```

Then:

```sh
chmod +x ~/.local/bin/macdef
macdef serendipity
```

This is offline, uses dictionaries you already have, and requires no API key or server. Its obvious drawback is that it
does nothing for your Debian desktop. The returned text can also be a little noisy because it reflects Dictionary.app’s
internal formatting and whichever dictionaries you have enabled.

## Tools I would not prioritize

I also examined several dedicated Wiktionary wrappers and small `define` projects. Many are thin HTML scrapers rather
than stable API clients, and some have very limited maintenance histories. Similarly, the `macdict` Python package wraps
macOS Dictionary Services but its latest PyPI release is from 2018. A transparent shell/API function or the small Swift
script above is easier to understand and maintain than adding one of these wrappers as another dependency.
([GitHub][11])

## My recommended setup

For your machines, I would initially install:

```sh
# macOS
brew install dict sdcv jq

# Debian
sudo apt install dict sdcv jq
```

Then use `dict` as your everyday `def` command, keep the HTTPS `define` function as a fallback for newer vocabulary or
networks that block DICT, and configure `sdcv` only when you find a dictionary dataset you are happy with. That gives
you a convenient online default, an HTTPS alternative, and a reliable offline path.

## Ranked list

1. **`dict`** — Best overall. It has the cleanest traditional command-line interface, works on both macOS and Debian,
   supports multiple dictionaries and spelling suggestions, and takes almost no work to start using. The unencrypted
   DICT protocol is its main weakness.

2. **`sdcv`** — Best offline choice. It is fast, private, scriptable, cross-platform, and supports JSON and fuzzy
   search. It ranks below `dict` only because locating and maintaining good StarDict dictionary files adds meaningful
   setup friction.

3. **A `curl` + `jq` HTTPS API function** — Best customizable choice. It offers modern data, HTTPS, examples, phonetics,
   and complete control over presentation. The trade-off is dependence on an external API and a little code of your own.

4. **WordNet’s `wn` command or a modern Open English WordNet wrapper** — Best specialized linguistic tool. Choose it
   when synonyms, antonyms, taxonomies, and semantic relationships matter as much as definitions. It is not as good as a
   general-purpose contemporary dictionary.

5. **A macOS Dictionary Services script** — Best Mac-specific option. It is offline and taps into Dictionary.app’s
   active sources, but its lack of Debian support makes it unsuitable as your primary cross-machine workflow.

[1]: https://manpages.debian.org/trixie/dict/dict.1.en.html "dict(1) — dict — Debian trixie — Debian Manpages"
[2]: https://datatracker.ietf.org/doc/rfc2229/?utm_source=chatgpt.com "RFC 2229 - A Dictionary Server Protocol"
[3]: https://curl.se/docs/tutorial.html?utm_source=chatgpt.com "curl - Tutorial"
[4]: https://manpages.debian.org/trixie/sdcv/sdcv.1.en.html "sdcv(1) — sdcv — Debian trixie — Debian Manpages"
[5]: https://freedict.org/ "Home — FreeDict"
[6]: https://dictionaryapi.dev/?utm_source=chatgpt.com "Free Dictionary API"
[7]: https://dictionaryapi.com/ "dictionaryapi.com"
[8]: https://wordnet.princeton.edu/documentation/wn1wn "wn(1WN) | WordNet"
[9]: https://wn.readthedocs.io/_/downloads/en/latest/pdf/ "wn"
[10]:
  https://developer.apple.com/documentation/coreservices/1446842-dcscopytextdefinition?language=objc
  "DCSCopyTextDefinition | Apple Developer Documentation"
[11]:
  https://github.com/words/wiktionary
  "GitHub - words/wiktionary: Look up words on wiktionary.org in English or any other language. · GitHub"

---

# Spell Checking CLI Tools

## Recommendation

For **checking one or more standalone words from a shell**, I would use **GNU Aspell**. It is a true dictionary-based
spell checker, has particularly useful correction suggestions, can process words through stdin, and can also
interactively check whole files. The current Homebrew formula installs an English dictionary along with Aspell, while
Debian packages the checker and English dictionary separately. ([Aspell][1])

I would pair it with **CSpell** only when checking source-code repositories. CSpell understands `CamelCase`,
`snake_case`, and programming-language vocabulary, making it considerably better than traditional spell checkers for
identifiers, comments, Markdown, and configuration files. ([CSpell][2])

## Installing and using Aspell

### macOS

```bash
brew install aspell
```

### Debian

```bash
sudo apt update
sudo apt install aspell aspell-en
```

Confirm that the American English dictionary is available:

```bash
aspell dump dicts | grep en_US
```

### Check whether a word is recognized

```bash
printf '%s\n' 'accomodate' |
  aspell --lang=en_US list
```

`aspell list` prints only unrecognized words:

- No output means the word was accepted.
- `accomodate` in the output means it was flagged.

This makes it useful inside scripts, although you need to test whether its output is empty rather than relying only on
the process exit code.

### Get spelling suggestions

```bash
printf '%s\n' 'accomodate' |
  aspell --lang=en_US pipe
```

Aspell’s pipe protocol returns a compact result:

- `*` means the word was accepted.
- `+` or `-` means it was accepted through an inflection or compound rule.
- `&` or `?` means it was rejected and suggestions follow.
- `#` means it was rejected without suggestions.

Aspell documents this as its Ispell-compatible pipe mode. ([Aspell][3])

### Interactively spell-check a file

```bash
aspell --lang=en_US check README.md
```

This opens an interactive terminal interface that steps through each suspected misspelling and lets you replace, ignore,
or add it to your personal dictionary.

## A convenient `spell` shell command

I would add the following to `~/.zshrc` on your Mac and `~/.bashrc` or `~/.zshrc` on Debian:

```bash
spell() {
  (( $# > 0 )) || {
    printf 'usage: spell WORD...\n' >&2
    return 2
  }

  local word result

  for word in "$@"; do
    result=$(
      printf '%s\n' "$word" |
        aspell --lang=en_US --encoding=utf-8 pipe |
        sed -n '2p'
    )

    case "$result" in
      \*|+*|-*)
        printf '✓ %s\n' "$word"
        ;;
      \&*|\?*)
        printf '✗ %s → %s\n' "$word" "${result#*: }"
        ;;
      \#*)
        printf '✗ %s (no suggestions)\n' "$word"
        ;;
      *)
        printf '? %s: %s\n' "$word" "$result"
        ;;
    esac
  done
}
```

Reload the shell:

```bash
source ~/.zshrc
```

Then use it like this:

```bash
spell accommodate
spell accomodate
spell separate definitely occurrence
```

This gives you the interface I think you are probably looking for: a simple `spell WORD...` command with a clear
correct/incorrect result and suggestions.

## How the main alternatives compare

| Tool          | How it works                                                                                    | Best use                                                                     | Main drawback                                                     |
| ------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **Aspell**    | Full dictionary and suggestion engine                                                           | Individual words, prose files, shell scripts                                 | Raw pipe output is terse without a wrapper                        |
| **CSpell**    | Dictionary checker designed around source-code tokenization                                     | Code, comments, Markdown, identifiers, CI                                    | Requires a JavaScript runtime and is heavier for one word         |
| **Hunspell**  | Dictionary plus sophisticated affix and morphology rules                                        | Multiple languages, complex inflections, LibreOffice-compatible dictionaries | Homebrew installs no dictionaries                                 |
| **Enchant**   | Consistent frontend that delegates to Aspell, Hunspell, Nuspell, AppleSpell, or another backend | One API across applications and systems                                      | Results depend on which backend is active                         |
| **typos-cli** | Database of known typo-to-correction mappings                                                   | Fast, low-noise repository and CI scanning                                   | Cannot reliably answer whether an arbitrary unknown word is valid |
| **Nuspell**   | Modern Hunspell-compatible Unicode spell engine                                                 | Rich morphology and Hunspell dictionaries                                    | Less turnkey as a standalone command                              |
| **codespell** | Database of common misspellings, primarily for source code                                      | Simple Python-based repository scanning                                      | Intentionally misses unknown or unusual mistakes                  |

### CSpell

Install it through npm:

```bash
npm install -g cspell
```

Check one word:

```bash
printf '%s\n' 'accomodate' |
  cspell stdin \
    --locale en-US \
    --show-suggestions \
    --no-progress \
    --no-summary
```

Check an entire repository:

```bash
cspell .
```

Or avoid a global installation:

```bash
npx cspell .
```

CSpell is self-contained, supports custom dictionaries, and recognizes programming-oriented word boundaries such as
`getUserConfiguration` and `get_user_configuration`. It can check stdin, individual files, globs, or entire directory
trees. ([CSpell][2])

Its principal downside for your immediate use is startup and output overhead. Invoking Node and CSpell merely to check
one word feels excessive compared with Aspell.

### Hunspell

Hunspell is a full spelling engine rather than a simple typo list. It is especially good for languages with rich
morphology, compound words, and affix rules, and it uses the widely available `.aff` and `.dic` dictionary format. Its
command-line input produces the same general style of accepted-word and suggestion results as Aspell. ([GitHub][4])

On Debian:

```bash
sudo apt install hunspell hunspell-en-us
```

Then:

```bash
printf '%s\n' 'accomodate' |
  hunspell -d en_US
```

The important macOS complication is that:

```bash
brew install hunspell
```

installs the engine but **no dictionaries**. Homebrew instructs users to supply compatible dictionaries under
`~/Library/Spelling/` or `/Library/Spelling/`. ([Homebrew Formulae][5])

That makes Hunspell less appealing than Aspell for a quick, reliable setup on your Mac, despite Hunspell being
technically excellent.

### Enchant

Enchant is not primarily another spelling engine. It is a broker that presents one consistent interface while delegating
to available backends such as Aspell, Hunspell, Nuspell, or macOS AppleSpell. ([RR Thomas][6])

Install it:

```bash
# macOS
brew install enchant

# Debian
sudo apt install enchant-2
```

Inspect the available providers and dictionaries:

```bash
enchant-lsmod-2 -list-dicts
```

Check a word:

```bash
printf '%s\n' 'accomodate' |
  enchant-2 -a -d en_US
```

Or list only misspellings:

```bash
printf '%s\n' 'accomodate' |
  enchant-2 -l -d en_US
```

Those `-a` and `-l` modes are part of Enchant’s documented CLI. ([RR Thomas][7])

Enchant is attractive when you want to use the same interface from multiple applications or reuse Apple’s system
spelling service. For a personal shell command, however, directly selecting Aspell is simpler and gives you more
predictable behavior across your Mac and Debian machine.

### `typos-cli`

`typos-cli` is a fast Rust tool built specifically for scanning repositories with few false positives:

```bash
brew install typos-cli
```

Or:

```bash
cargo install typos-cli --locked
```

Scan the current repository:

```bash
typos
```

Apply unambiguous corrections:

```bash
typos --write-changes
```

Check stdin:

```bash
printf '%s\n' 'accomodate' | typos -
```

Its low false-positive rate comes from an important design choice: it maintains known typo corrections rather than
treating every token absent from a complete dictionary as an error. Consequently, it may catch `accomodate` but ignore a
novel nonsensical spelling that Aspell or CSpell would flag. ([GitHub][8])

That is excellent behavior for unattended CI, but it is not the right semantic model for a general `spell WORD` command.

### Nuspell

Nuspell is a modern C++ spell-checking engine with full Unicode support and compatibility with Hunspell dictionaries. It
supports complex morphology and compounds and provides a command-line executable. ([GitHub][9])

On macOS:

```bash
brew install nuspell
```

Typical file usage is:

```bash
nuspell -d en_US document.txt
```

It is technically compelling, particularly for non-English languages, but it still requires suitable Hunspell-compatible
dictionaries. For this use case, it does not offer enough practical advantage over Aspell or Hunspell to justify the
additional setup.

### `codespell`

`codespell` is a mature Python option:

```bash
pip install codespell
```

Scan a repository:

```bash
codespell
```

Check stdin:

```bash
printf '%s\n' 'accomodate' | codespell -
```

Like `typos-cli`, it checks a collection of known common misspellings rather than a complete vocabulary. Its own
documentation explicitly notes that it can catch a known transposition such as `adn` while potentially ignoring
arbitrary nonsense. ([GitHub][10])

It remains useful for Python-oriented pre-commit workflows, but `typos-cli` generally occupies the same niche with
better performance, while CSpell performs more comprehensive code-aware checking.

## Two limitations shared by these tools

A single-word spell checker cannot tell whether a correctly spelled word is contextually appropriate. It will accept
both `their` and `there`, and it will accept both `form` and `from`. Detecting those errors requires sentence-level
grammar checking rather than dictionary lookup.

Technical names will also produce false positives in traditional dictionaries. For ordinary prose, add recurring names
to an Aspell personal dictionary. For source code containing terms such as `LangGraph`, `BigQuery`, `proto3`, or
project-specific identifiers, CSpell’s project dictionary is usually the better solution.

## Ranked tools to consider

1. **GNU Aspell — best overall for your stated need.** It provides the most direct path to a fast `spell WORD...`
   command, offers useful suggestions, works on both macOS and Debian, and Homebrew’s package includes an English
   dictionary. ([Aspell][3])

2. **CSpell — best for source code, documentation, and CI.** Choose this over Aspell when your input contains
   identifiers, programming terminology, Markdown, or complete repositories. Its support for `CamelCase`, `snake_case`,
   custom dictionaries, stdin, globs, and language-specific vocabulary is highly relevant to software-development work.
   ([CSpell][2])

3. **Hunspell — best full spell checker for multilingual or morphologically complex languages.** It is a powerful engine
   with an enormous compatible dictionary ecosystem, but the lack of bundled dictionaries in Homebrew prevents it from
   being as turnkey as Aspell on your Mac. ([GitHub][4])

4. **Enchant — best abstraction layer.** Use it when you specifically value one interface capable of selecting among
   Aspell, Hunspell, Nuspell, and AppleSpell. It loses points because the same command can behave differently depending
   on the installed provider. ([RR Thomas][6])

5. **typos-cli — best fast, low-noise repository scanner.** It is especially attractive for monorepos, pre-commit hooks,
   and unattended CI, but it is not a complete arbitrary-word validator. ([GitHub][8])

6. **Nuspell — best modern Hunspell-compatible engine.** Its Unicode and morphology support are impressive, but
   dictionary management and a less convenient standalone workflow make it harder to recommend for simple terminal
   lookups. ([GitHub][9])

7. **codespell — a solid lightweight Python option.** It is easy to integrate into Python projects and catches many
   common mistakes, but its known-misspelling model is less comprehensive than CSpell and less suitable than Aspell for
   checking arbitrary words. ([GitHub][10])

[1]: https://aspell.net/?utm_source=chatgpt.com "GNU Aspell"
[2]: https://cspell.org/docs/api/cspell "cspell | CSpell"
[3]: https://aspell.net/man-html/Through-A-Pipe.html?utm_source=chatgpt.com "6.2 Through A Pipe"
[4]: https://github.com/hunspell/hunspell "GitHub - hunspell/hunspell: The most popular spellchecking library. · GitHub"
[5]: https://formulae.brew.sh/formula/hunspell "Homebrew Formulae: hunspell"
[6]: https://rrthomas.github.io/enchant/ "Enchant"
[7]: https://rrthomas.github.io/enchant/src/enchant-2.html "ENCHANT-2"
[8]: https://github.com/crate-ci/typos "GitHub - crate-ci/typos: Source code spell checker · GitHub"
[9]: https://github.com/nuspell/nuspell "GitHub - nuspell/nuspell: 🖋️ Fast and safe spellchecking C++ library · GitHub"
[10]:
  https://github.com/codespell-project/codespell
  "GitHub - codespell-project/codespell: check code for common misspellings · GitHub"
