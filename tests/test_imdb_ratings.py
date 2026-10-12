import gzip

from app.integrations.imdb_datasets import iter_ratings


def test_iter_ratings(tmp_path):
    f = tmp_path / "r.tsv.gz"
    with gzip.open(f, "wt", encoding="utf-8") as fh:
        fh.write("tconst\taverageRating\tnumVotes\ntt0068646\t9.2\t2100000\ntt0000001\t5.7\t2000\n")
    assert list(iter_ratings(f)) == [("tt0068646", 9.2, 2100000), ("tt0000001", 5.7, 2000)]
