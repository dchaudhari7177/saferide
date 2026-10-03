# Hugging Face public-card refresh — 19 August 2026

SafeRide refreshed the public README/model-card text for the current mobile
model, adapter, training dataset, and superseded Gemma 3n record so every card
points to the canonical repository at
`https://github.com/esherialabs/saferide`.

| Surface | Verified revision | README SHA-256 |
| --- | --- | --- |
| Gemma 4 E2B LiteRT-LM mobile model | `ce0b969d2ef747b43b91b7278cf1c297efc0f666` | `6393df8623761e80130e9d0d3e35dd48f4800c85973cf42d21b37016ca706955` |
| Gemma 4 E2B adapter | `42d98ef60eddcc280e1e3c3a0b78ff44842c1d98` | `626cdf31113945333562f57c9949d661b563c76b324058d71179a9439b53b82b` |
| Gemma 4 E2B training dataset | `da760c09e0d51e929778d10db749b5bb60cfa70c` | `f89af8927520ef99816b384d5e648decb69547f0becd22446b2da61802ac2ba2` |
| Superseded Gemma 3n card | `a1f511656e759927bcab2af6ff87e129e2c4689f` | `25b89d9dedd83b4bd5db3a3009550aec902aac9bf92a5c3ac6953009632357dd` |

The publication script verified each README anonymously after publication and
compared the complete non-README inventory before and after. Model weights,
adapter files, tokenizer/configuration files, dataset artifacts, and other
non-card bytes were unchanged.

The legacy Gemma 3n repository remains clearly marked as superseded and must
not be treated as the current Android model or release-readiness evidence.
