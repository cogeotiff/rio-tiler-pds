import pytest

from rio_tiler_pds.landsat.utils import sceneid_parser

# sceneid,expected_content
LANDSAT_SCENE_PARSER_TEST_CASES = (
    # Collection 2 Level 2 OLI-TIRS 8 SP (both SR and ST)
    (
        "LC08_L2SP_001062_20201031_20201106_02_T2",
        {
            "sensor": "C",
            "satellite": "08",
            "processingCorrectionLevel": "L2SP",
            "path": "001",
            "row": "062",
            "acquisitionYear": "2020",
            "acquisitionMonth": "10",
            "acquisitionDay": "31",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "06",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LC08_L2SP_001062_20201031_20201106_02_T2",
            "date": "2020-10-31",
            "_processingLevelNum": "2",
            "_sensor": "oli-tirs",
        },
    ),
    # Collection 2 Level 2 OLI-TIRS 8 SR (no ST)
    (
        "LC08_L2SR_122108_20201031_20201106_02_T2",
        {
            "sensor": "C",
            "satellite": "08",
            "processingCorrectionLevel": "L2SR",
            "path": "122",
            "row": "108",
            "acquisitionYear": "2020",
            "acquisitionMonth": "10",
            "acquisitionDay": "31",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "06",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LC08_L2SR_122108_20201031_20201106_02_T2",
            "date": "2020-10-31",
            "_processingLevelNum": "2",
            "_sensor": "oli-tirs",
        },
    ),
    # Collection 2 Level 2 TM SP (both SR and ST)
    (
        "LT05_L2SP_014032_20111018_20200820_02_T1",
        {
            "sensor": "T",
            "satellite": "05",
            "processingCorrectionLevel": "L2SP",
            "path": "014",
            "row": "032",
            "acquisitionYear": "2011",
            "acquisitionMonth": "10",
            "acquisitionDay": "18",
            "processingYear": "2020",
            "processingMonth": "08",
            "processingDay": "20",
            "collectionNumber": "02",
            "collectionCategory": "T1",
            "scene": "LT05_L2SP_014032_20111018_20200820_02_T1",
            "date": "2011-10-18",
            "_processingLevelNum": "2",
            "_sensor": "tm",
        },
    ),
    # Collection 2 Level 2 TM SR (no ST)
    (
        "LT05_L2SR_089076_20110929_20200820_02_T2",
        {
            "sensor": "T",
            "satellite": "05",
            "processingCorrectionLevel": "L2SR",
            "path": "089",
            "row": "076",
            "acquisitionYear": "2011",
            "acquisitionMonth": "09",
            "acquisitionDay": "29",
            "processingYear": "2020",
            "processingMonth": "08",
            "processingDay": "20",
            "collectionNumber": "02",
            "collectionCategory": "T2",
            "scene": "LT05_L2SR_089076_20110929_20200820_02_T2",
            "date": "2011-09-29",
            "_processingLevelNum": "2",
            "_sensor": "tm",
        },
    ),
    # Collection 2 Level 2 ETM SP (both SR and ST)
    (
        "LE07_L2SP_175066_20201026_20201121_02_T1",
        {
            "sensor": "E",
            "satellite": "07",
            "processingCorrectionLevel": "L2SP",
            "path": "175",
            "row": "066",
            "acquisitionYear": "2020",
            "acquisitionMonth": "10",
            "acquisitionDay": "26",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "21",
            "collectionNumber": "02",
            "collectionCategory": "T1",
            "scene": "LE07_L2SP_175066_20201026_20201121_02_T1",
            "date": "2020-10-26",
            "_processingLevelNum": "2",
            "_sensor": "etm",
        },
    ),
    # Collection 2 Level 2 ETM SR (no ST)
    (
        "LE07_L2SR_123067_20201030_20201126_02_T1",
        {
            "sensor": "E",
            "satellite": "07",
            "processingCorrectionLevel": "L2SR",
            "path": "123",
            "row": "067",
            "acquisitionYear": "2020",
            "acquisitionMonth": "10",
            "acquisitionDay": "30",
            "processingYear": "2020",
            "processingMonth": "11",
            "processingDay": "26",
            "collectionNumber": "02",
            "collectionCategory": "T1",
            "scene": "LE07_L2SR_123067_20201030_20201126_02_T1",
            "date": "2020-10-30",
            "_processingLevelNum": "2",
            "_sensor": "etm",
        },
    ),
)


@pytest.mark.parametrize("sceneid,expected_content", LANDSAT_SCENE_PARSER_TEST_CASES)
def test_landsat_sceneid_parser(sceneid, expected_content):
    """Parse landsat valid collection1 sceneid and return metadata."""
    assert sceneid_parser(sceneid) == expected_content
