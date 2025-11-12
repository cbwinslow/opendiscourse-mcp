import os
import tempfile
from mcp_server.utils.xml_ingest import ingest_xml_to_df
import pandas as pd

SAMPLE_XML = '''<?xml version="1.0"?>
<root>
  <record>
    <id>doc1</id>
    <title>Test Document</title>
    <date>2025-11-12</date>
  </record>
  <record>
    <id>doc2</id>
    <title>Second Document</title>
    <date>2025-11-11</date>
  </record>
</root>
'''


def test_ingest_xml_to_df_creates_dataframe():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, 'sample.xml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_XML)
        df = ingest_xml_to_df(path, record_xpath='.//record')
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] == 2
        assert 'id' in df.columns
        assert df.loc[0, 'id'] == 'doc1'
        assert df.loc[1, 'title'] == 'Second Document'
