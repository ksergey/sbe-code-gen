// Copyright (c) Sergey Kovalevich <inndie@gmail.com>
// SPDX-License-Identifier: MIT

#include <algorithm>
#include <array>
#include <cstdio>
#include <expected>
#include <format>
#include <string>
#include <string_view>

#include <cxxopts.hpp>
#include <nlohmann/json.hpp>

#include "sbe/FixBinary/schema.h"
#include "sbe/b3-market-data-messages-1.3.1/schema.h"
#include "sbe/spot_2_0/schema.h"
#include "sbe/spot_3_1/schema.h"

template <std::size_t N>
struct CtString {
    char data[N];

    consteval CtString(char const* str) noexcept {
        std::copy_n(str, N, data);
    }

    [[nodiscard]] constexpr operator std::string_view() const noexcept {
        return std::string_view{data, N - 1};
    }
};

template <std::size_t N>
CtString(char const (&)[N]) -> CtString<N>;

template <typename...>
struct TypeList {};

// Schema info
template <CtString SchemaName, typename MessageList>
struct SchemaInfo {
    // Schema name
    static constexpr auto name = static_cast<std::string_view>(SchemaName);
    // List of schema messages
    using Messages = MessageList;
};

// clang-format off
using Schemas = TypeList<
    SchemaInfo<"FixBinary", FixBinary::Messages>,
    SchemaInfo<"spot_2_0", spot_2_0::Messages>,
    SchemaInfo<"spot_3_1", spot_3_1::Messages>
>;
// clang-format on

[[nodiscard]] auto getAvailableSbeSchemas() noexcept {
    return []<template <typename...> typename List, typename... Ts>(List<Ts...>) {
        return std::array<std::string_view, sizeof...(Ts)>{Ts::name...};
    }(Schemas{});
}

// Return true on message exists in schema
[[nodiscard]] auto messageExists(std::string_view schemaName, std::string_view messageName) noexcept
    -> std::expected<void, std::string> {
    auto const schemaExists = [&]<template <typename...> typename List, typename... Ts>(List<Ts...>) {
        return (false || ... || (schemaName == Ts::name));
    }(Schemas{});
    if (!schemaExists) {
        return std::unexpected(std::format("unknown schema \"{}\"", schemaName));
    }
    auto isMessageExists = [&]<template <typename...> typename List, typename... Ts>(List<Ts...>) {
        return (false || ... || (messageName == Ts::sbeMessageName()));
    };
    auto const messageExists = [&]<template <typename...> typename List, typename... Ts>(List<Ts...>) {
        return (false || ... || (schemaName == Ts::name ? isMessageExists(typename Ts::Messages{}) : false));
    }(Schemas{});
    if (!messageExists) {
        return std::unexpected(std::format("message \"{}\" not found in schema \"{}\"", messageName, schemaName));
    }
    return {};
}

template <typename M>
struct Message {};

template <typename Fn>
void process(std::string_view schemaName, std::string_view messageName, Fn fn) {
    auto invokeMsg = [&]<template <typename...> typename List, typename... Ts>(List<Ts...>) {
        return (false || ... || (messageName == Ts::sbeMessageName() ? (fn(Message<Ts>{}), true) : false));
    };
    [&]<template <typename...> typename List, typename... Ts>(List<Ts...>) {
        return (false || ... || (schemaName == Ts::name ? (invokeMsg(typename Ts::Messages{}), true) : false));
    }(Schemas{});
}

template <typename F>
void describeField(int indent = 1) noexcept;

template <template <typename...> typename List, typename... Ts>
void describeFields(List<Ts...>, [[maybe_unused]] int indent = 1) noexcept {
    (describeField<Ts>(indent), ...);
}

template <typename F>
void describeField(int indent) noexcept {
    (void)indent;

    // TODO: indent
    if constexpr (requires { F::sbeRefName(); }) {
        if constexpr (requires { F::sbeGroupName(); }) {
            std::fprintf(stdout, "%*s Group: %s (%s)\n", indent * 2, "", F::sbeRefName(), F::sbeGroupName());
            std::fprintf(stdout, "%*s  BlockLength: %d\n", indent * 2, "", F::sbeBlockLength());
        } else {
            std::fprintf(stdout, "%*s Field: %s\n", indent * 2, "", F::sbeRefName());
        }
    } else {
        std::fprintf(stdout, "%*s WTF?\n", indent * 2, "");
    }

    if constexpr (requires { typename F::Fields; }) {
        describeFields(typename F::Fields{}, indent + 1);
    }
}

template <typename M>
void describe() noexcept {
    std::fprintf(stdout, "MessageName: %s\n", M::sbeMessageName());
    std::fprintf(stdout, "TemplateId: %d\n", int(M::sbeTemplateId()));
    std::fprintf(stdout, "BlockLength: %d\n", int(M::sbeBlockLength()));
    std::fprintf(stdout, "SchemaId: %d\n", int(M::sbeSchemaId()));
    std::fprintf(stdout, "Version: %d\n", int(M::sbeVersion()));

    describeFields(typename M::Fields{});
}

auto main(int argc, char* argv[]) -> int {
    try {
        cxxopts::Options options{"sbe-tool", "sbe encode/decode tool for schemes"};
        options.set_width(120);
        options.set_tab_expansion();

        // clang-format off
        options.add_options()
            ("e,encode", "encode message")
            ("d,decode", "decode message")
            ("s,schema", "schema name", cxxopts::value<std::string>())
            ("m,message", "schema's message name", cxxopts::value<std::string>())
            ("h,help", "print help and exit")
        ;
        // clang-format on

        auto args = options.parse(argc, argv);
        if (args.count("help")) {
            std::fprintf(stdout, "%s\n", options.help().c_str());
            std::fprintf(stdout, "Available schemas:\n");
            for (auto schemaName : getAvailableSbeSchemas()) {
                std::fprintf(stdout, " - %.*s\n", static_cast<int>(schemaName.length()), schemaName.data());
            }
            return EXIT_SUCCESS;
        }

        if (args.count("encode") && args.count("decode")) {
            std::fprintf(stderr, "ERROR: --encode and --decode used simultaneously\n");
            return EXIT_FAILURE;
        }

        if (!args.count("schema")) {
            std::fprintf(stderr, "ERROR: --schema not set\n");
            return EXIT_FAILURE;
        }
        auto const& schema = args["schema"].as<std::string>();

        if (!args.count("message")) {
            std::fprintf(stderr, "ERROR: --message not set\n");
            return EXIT_FAILURE;
        }
        auto const& message = args["message"].as<std::string>();

        if (auto const rc = messageExists(schema, message); !rc) {
            std::fprintf(stderr, "ERROR: %s\n", rc.error().c_str());
            return EXIT_FAILURE;
        }

        if (args.count("encode")) {
            // Do encode
            process(schema, message, []<typename M>(Message<M>) {
                std::printf("encode: %s (%d)\n", M::sbeMessageName(), int(M::sbeTemplateId()));
                describe<M>();
            });
        } else if (args.count("decode")) {
            // Do decode
            process(schema, message, []<typename M>(Message<M>) {
                std::printf("decode: %s (%d)\n", M::sbeMessageName(), int(M::sbeTemplateId()));
                describe<M>();
            });
        } else {
            std::fprintf(stderr, "ERROR: what to do?\n");
            return EXIT_FAILURE;
        }

    } catch (std::exception const& e) {
        std::fprintf(stderr, "ERROR: %s\n", e.what());
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
