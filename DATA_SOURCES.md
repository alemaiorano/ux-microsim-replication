# Data Sources

The proxy corpora used in the paper are **public third-party datasets**. They
are **not redistributed** in this package, to respect their original licenses.
Each is cited in `paper_ux/references.bib`; retrieve them from the source listed
below before re-running any artifact-derivation step that needs raw text.

The result artifacts under `reports/ux/` are aggregates computed from these
corpora and are sufficient to verify every number in the paper without
re-downloading the raw data.

## App-review proxies

| Dataset | Description | Source | `references.bib` key |
|---|---|---|---|
| Tinder (Google Play) | English app reviews with ratings | Kaggle — "Tinder Google Play Store Review" | `kaggle_tinder` |
| Gojek (Google Play) | Indonesian app reviews with ratings | Kaggle — "Gojek Playstore Reviews" | `kaggle_gojek` |

## Support-conversation proxy

| Dataset | Description | Source | `references.bib` key |
|---|---|---|---|
| Customer Support on Twitter | Customer-support tweets (no star ratings) | Kaggle — "Customer Support on Twitter" | `kaggle_twitter_support` |

## Amazon Appstore proxies

| Dataset | Description | Source | `references.bib` key |
|---|---|---|---|
| Amazon Appstore (Low-rated) | Low-rated Amazon Appstore reviews | "Dataset of user reviews from low-rated Amazon Appstore applications" | `amazonlowrated2026dataset` |
| Amazon Appstore (Annotated) | Labeled subset with issue-type categories | Same dataset as above (annotated subset) | `amazonlowrated2026dataset` |

## OSS issues proxy (B2B)

GitHub issues from the following observability repositories, sampled for
feasibility (no redistribution — retrieve via the GitHub API):

- `grafana/grafana`
- `prometheus/prometheus`
- `open-telemetry/opentelemetry-collector`
- `open-telemetry/opentelemetry-js`
- `jaegertracing/jaeger`
- `openzipkin/zipkin`
- `getsentry/sentry`

## Retrieval notes

- Exact URLs and citation details are in `paper_ux/references.bib`.
- The embedding-alignment experiments operate on capped/subsampled slices of the
  larger corpora; the sampling settings are reported in the paper (Section 4 and
  Section 5) and reflected in the artifact file names under `reports/ux/`.
- The local embedding model used for embedding alignment is BGE-M3, run via
  Ollama; it is not redistributed here.
