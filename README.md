[<img src="https://img.shields.io/github/license/ksergey/sbe-code-gen">](https://opensource.org/license/gpl-3-0)
[<img src="https://img.shields.io/github/actions/workflow/status/ksergey/sbe-code-gen/on_push.yml?logo=linux">](https://github.com/ksergey/sbe-code-gen/actions/workflows/on_push.yml)
[<img src="https://img.shields.io/badge/language-python3-yellow">](https://en.wikipedia.org/wiki/Python_(programming_language))
[<img src="https://img.shields.io/badge/language-C%2B%2B23-red">](https://en.wikipedia.org/wiki/C%2B%2B23)

# sbe-code-gen

Simple Binary Encoding codec generator for C++20, C++23, Python [WIP]

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
