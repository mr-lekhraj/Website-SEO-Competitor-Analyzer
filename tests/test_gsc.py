from io import BytesIO
import pytest
from src.gsc import parse_gsc_csv, gsc_api_rows_to_frame


def test_parse_gsc_top_queries_with_percentage_ctr():
    raw = b"Top queries,Clicks,Impressions,CTR,Position\\nmolarity calculator,12,300,4%,7.5\\nsample size calculator,5,100,5%,9.0\\n"
    result = parse_gsc_csv(BytesIO(raw))
    assert list(result.columns) == ["query", "page", "clicks", "impressions", "ctr", "position"]
    assert result.iloc[0]["query"] == "molarity calculator"
    assert result.iloc[0]["ctr"] == pytest.approx(0.04)


def test_parse_gsc_query_page_export():
    raw = b"Query,Page,Clicks,Impressions,CTR,Position\\nmolarity calculator,https://site.test/a,4,40,10%,4.5\\nmolarity calculator,https://site.test/b,2,20,10%,8.0\\n"
    result = parse_gsc_csv(BytesIO(raw))
    assert len(result) == 2
    assert set(result["page"]) == {"https://site.test/a", "https://site.test/b"}


def test_gsc_requires_query_column():
    with pytest.raises(ValueError):
        parse_gsc_csv(BytesIO(b"Clicks,Impressions\\n1,10\\n"))


def test_api_rows_normalization():
    result = gsc_api_rows_to_frame([{"keys": ["molarity", "https://site.test/"], "clicks": 2, "impressions": 20, "ctr": .1, "position": 3}])
    assert result.iloc[0]["query"] == "molarity"
    assert result.iloc[0]["page"] == "https://site.test/"
