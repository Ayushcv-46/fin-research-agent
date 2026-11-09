from retrieval.bm25 import bm25_scores, reciprocal_rank_fusion


def test_bm25_prefers_exact_keyword_match():
    scores = bm25_scores("supply chain concentration", [
        "Revenue grew year over year.",
        "Supply chain concentration creates a risk.",
    ])
    assert scores[1] > scores[0]


def test_rrf_promotes_result_present_in_both_rankings():
    dense = [{"id": "a", "text": "semantic"}, {"id": "b", "text": "shared"}]
    lexical = [{"id": "b", "text": "shared"}, {"id": "c", "text": "keyword"}]
    fused = reciprocal_rank_fusion(dense, lexical, limit=3)
    assert fused[0]["id"] == "b"


def test_rrf_is_stable_for_single_ranked_list():
    results = reciprocal_rank_fusion([{"id": "x", "text": "x"}], limit=1)
    assert results[0]["id"] == "x"
