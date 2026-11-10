# BM25 answerability calibration — dpr-pilot-v0.8

## Method

Each workspace uses its own BM25 top-score threshold. The threshold was selected on the 62-query dev split (56 answerable and 6 unanswerable) by maximizing balanced accuracy. Ties prefer higher specificity, then the higher threshold. The fixed threshold was applied to the 24-query test split (18 answerable and 6 unanswerable).

## Results

| Chunking strategy | Dev threshold | Test TP | Test FP | Test TN | Test FN | Test recall | Test specificity | Test balanced accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fixed size | 11.329658607140283 | 15 | 2 | 4 | 3 | 0.8333 | 0.6667 | 0.7500 |
| Recursive | 13.265493560658861 | 14 | 0 | 6 | 4 | 0.7778 | 1.0000 | 0.8889 |
| Sentence window | 14.146471361769521 | 14 | 0 | 6 | 4 | 0.7778 | 1.0000 | 0.8889 |

TP = answerable queries classified answerable; FP = unanswerable queries classified answerable; TN = unanswerable queries classified unanswerable; FN = answerable queries classified unanswerable.

## Limits

Only six unanswerable examples were used for calibration and six for test, so each error changes a rate substantially. The unanswerable questions are out-of-domain queries; these results do not establish performance on subtle, in-domain questions that lack supporting evidence. Thresholds are specific to each workspace's chunking configuration and BM25 settings. These results are descriptive and do not establish that one chunking strategy is generally superior.
