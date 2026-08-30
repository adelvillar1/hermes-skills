# Structured LLM Output in Swift

Requesting JSON from local Ollama/DeepSeek models and decoding into `Codable` types.

## The Pattern

```swift
struct LLMSummaryResponse: Codable, Sendable {
    let overallSummary: String?
    let actionItems: [String]?
    let speakerSummaries: [SpeakerSummary]?
}

extension LLMClient {
    func chatStructured<T: Codable & Sendable>(
        messages: [Message],
        responseType: T.Type
    ) async throws -> T {
        let response = try await chat(
            messages: messages,
            responseFormat: .json  // passes `{ type: "json_object" }`
        )
        // Strip markdown fences if present
        let cleaned = response.content
            .replacingOccurrences(of: "```json", with: "")
            .replacingOccurrences(of: "```", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard let data = cleaned.data(using: .utf8) else {
            throw LLMError.invalidResponse
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
}
```

## Markdown Fence Handling

Local models frequently wrap JSON in ` ```json ` fences. Always strip fences before `JSONDecoder`. The `ollama-json-markdown-fences` skill has a more robust regex-based stripper.

## Fallback Strategy

If `JSONDecoder` fails, degrade gracefully:

```swift
do {
    let structured = try await client.chatStructured(
        messages: messages,
        responseType: LLMSummaryResponse.self
    )
    return structured
} catch {
    // Fallback to flat text extraction
    let flat = try await client.chat(messages: messages)
    return LLMSummaryResponse(
        overallSummary: flat.content,
        actionItems: nil,
        speakerSummaries: nil
    )
}
```

This ensures the feature works even when the model emits malformed JSON.
