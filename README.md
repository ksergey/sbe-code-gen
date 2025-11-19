[<img src="https://img.shields.io/github/license/ksergey/sbe-code-gen">](https://opensource.org/license/gpl-3-0)
[<img src="https://img.shields.io/github/actions/workflow/status/ksergey/sbe-code-gen/on_push.yml?logo=linux">](https://github.com/ksergey/sbe-code-gen/actions/workflows/on_push.yml)
[<img src="https://img.shields.io/badge/language-python3-yellow">](https://en.wikipedia.org/wiki/Python_(programming_language))
[<img src="https://img.shields.io/badge/language-C%2B%2B23-red">](https://en.wikipedia.org/wiki/C%2B%2B23)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ksergey/sbe-code-gen)

# sbe-code-gen (WIP)

A code generator that produces high-performance binary codecs from Simple Binary Encoding (SBE) XML schemas.
The tool generates codec implementations in multiple programming languages (C++, Python) that can encode and decode binary messages according to the SBE specification.

* spec https://github.com/FIXTradingCommunity/fix-simple-binary-encoding
* inspired by https://github.com/real-logic/simple-binary-encoding

# TODO

- [x] nested composite enum/set/composite types
- [ ] tests
- [x] ci integration
- [x] cmake integration
- [ ] rust support?
- [x] python support
- [x] (cppng) from/to json serialization
- [ ] (cppng) set/get fixed-length strings as variable length string (trim till '\0')
- [ ] (cppng) calculate buffer size for a message
- [ ] tests
- [ ] examples
- [ ] docs
