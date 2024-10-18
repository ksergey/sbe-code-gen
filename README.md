# sbe-code-gen

Simple Binary Encoding codec generator for C++20 [WIP]

* spec https://github.com/FIXTradingCommunity/fix-simple-binary-encoding
* inspired by https://github.com/real-logic/simple-binary-encoding

# TODO

- [x] nested composite enum/set/composite types
- [ ] tests
- [ ] ci integration
- [x] cmake integration
- [ ] rust support?
- [ ] python support?
- [x] (cppng) from/to json serialization ([impl](example/example_json.cpp))
- [x] (cppng) set/get fixed-length strings as variable length string (trim till '\0')
- [ ] (cppng) calculate buffer size for a message
- [ ] tests
