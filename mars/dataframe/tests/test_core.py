# Copyright 1999-2021 Alibaba Group Holding Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import pandas as pd
import pytest

from mars.core import tile
from mars.dataframe import cut
from mars.dataframe.initializer import DataFrame, Series, Index
from mars.lib.groupby_wrapper import wrapped_groupby


def test_dataframe_params():
    raw = pd.DataFrame({'a': [1, 2, 3]})
    df = DataFrame(raw)
    df = df[df['a'] < 2]
    df = tile(df)
    c = df.chunks[0]

    assert any(np.isnan(s) for s in c.params['shape'])
    assert np.isnan(c.params['index_value'].min_val)
    c.params = c.get_params_from_data(raw[raw['a'] < 2])
    # shape and index_value updated
    assert not any(np.isnan(s) for s in c.params['shape'])
    assert not np.isnan(c.params['index_value'].min_val)

    params = c.params.copy()
    params.pop('index', None)
    df.params = params
    assert np.prod(df.shape) > 0
    df.refresh_params()


def test_series_params():
    raw = pd.Series([1, 2, 3], name='a')
    series = Series(raw)
    series = series[series < 2]
    series = tile(series)
    c = series.chunks[0]

    assert any(np.isnan(s) for s in c.params['shape'])
    assert np.isnan(c.params['index_value'].min_val)
    c.params = c.get_params_from_data(raw[raw < 2])
    # shape and index_value updated
    assert not any(np.isnan(s) for s in c.params['shape'])
    assert not np.isnan(c.params['index_value'].min_val)

    params = c.params.copy()
    params.pop('index', None)
    series.params = params
    assert np.prod(series.shape) > 0
    series.refresh_params()


def test_index_params():
    raw = pd.Series([1, 2, 3], name='a')
    raw.index.name = 'b'
    series = Series(raw)
    series = series[series < 2]
    index = series.index
    index = tile(index)
    c = index.chunks[0]

    assert any(np.isnan(s) for s in c.params['shape'])
    assert np.isnan(c.params['index_value'].min_val)
    c.params = c.get_params_from_data(raw[raw < 2].index)
    # shape and index_value updated
    assert not any(np.isnan(s) for s in c.params['shape'])
    assert not np.isnan(c.params['index_value'].min_val)

    params = c.params.copy()
    params.pop('index', None)
    index.params = params
    assert np.prod(index.shape) > 0
    index.refresh_params()


def test_categorical_params():
    raw = np.random.rand(10)
    cate = cut(raw, [0.3, 0.5, 0.7])
    cate = tile(cate)
    c = cate.chunks[0]

    c.params = c.get_params_from_data(pd.cut(raw, [0.3, 0.5, 0.7]))
    assert len(c.params['categories_value'].to_pandas()) > 0

    params = c.params.copy()
    params.pop('index', None)
    cate.params = params
    assert len(cate.params['categories_value'].to_pandas()) > 0
    cate.refresh_params()


def test_groupby_params():
    raw = pd.DataFrame({'a': [1, 2, 3]})
    df = DataFrame(raw)
    grouped = df.groupby('a')
    grouped = tile(grouped)
    c = grouped.chunks[0]

    c.params = c.get_params_from_data(wrapped_groupby(raw, by='a'))
    params = c.params.copy()
    params.pop('index', None)
    grouped.params = params

    raw = pd.Series([1, 2, 3], name='a')
    series = Series(raw)
    grouped = series.groupby(level=0)
    grouped = tile(grouped)
    c = grouped.chunks[0]

    c.params = c.get_params_from_data(wrapped_groupby(raw, level=0))
    params = c.params.copy()
    params.pop('index', None)
    grouped.params = params
    grouped.refresh_params()


def test_dataframe_dir():
    df = DataFrame(pd.DataFrame(np.random.rand(4, 3), columns=list('ABC')))
    dir_result = set(dir(df))
    for c in df.dtypes.index:
        assert c in dir_result


def test_to_frame_or_series(setup):
    raw = pd.Series(np.random.rand(10), name='col')
    series = Series(raw)

    r = series.to_frame()
    result = r.execute().fetch()
    pd.testing.assert_frame_equal(raw.to_frame(), result)

    r = series.to_frame(name='new_name')
    result = r.execute().fetch()
    pd.testing.assert_frame_equal(raw.to_frame(name='new_name'), result)

    series = series[series > 0.1]
    r = series.to_frame(name='new_name')
    result = r.execute().fetch()
    pd.testing.assert_frame_equal(raw[raw > 0.1].to_frame(name='new_name'), result)

    raw = pd.Index(np.random.rand(10), name='col')
    index = Index(raw)

    r = index.to_frame()
    result = r.execute().fetch()
    pd.testing.assert_frame_equal(raw.to_frame(), result)

    r = index.to_frame(index=False)
    result = r.execute().fetch()
    pd.testing.assert_frame_equal(raw.to_frame(index=False), result)

    r = index.to_frame(name='new_name')
    result = r.execute().fetch()
    pd.testing.assert_frame_equal(raw.to_frame(name='new_name'), result)

    r = index.to_series()
    result = r.execute().fetch()
    pd.testing.assert_series_equal(raw.to_series(), result)

    r = index.to_series(index=pd.RangeIndex(0, 10))
    result = r.execute().fetch()
    pd.testing.assert_series_equal(raw.to_series(index=pd.RangeIndex(0, 10)), result)

    r = index.to_series(name='new_name')
    result = r.execute().fetch()
    pd.testing.assert_series_equal(raw.to_series(name='new_name'), result)

    raw = pd.MultiIndex.from_tuples([('A', 'E'), ('B', 'F'), ('C', 'G')])
    index = Index(raw, tupleize_cols=True)

    r = index.to_frame()
    result = r.execute().fetch()
    pd.testing.assert_frame_equal(raw.to_frame(), result)

    with pytest.raises(TypeError):
        index.to_frame(name='XY')

    with pytest.raises(ValueError):
        index.to_frame(name=['X', 'Y', 'Z'])

    r = index.to_frame(name=['X', 'Y'])
    result = r.execute().fetch()
    pd.testing.assert_frame_equal(raw.to_frame(name=['X', 'Y']), result)

    r = index.to_series(name='new_name')
    result = r.execute().fetch()
    pd.testing.assert_series_equal(raw.to_series(name='new_name'), result)


def test_assign(setup):
    rs = np.random.RandomState(0)
    raw = pd.DataFrame({"A": rs.rand(10), "B": rs.rand(10)})

    df = DataFrame(raw, chunk_size=5)
    result = df.assign(C=df.B / df.A).execute().fetch()
    expected = raw.assign(C=raw.B / raw.A)
    pd.testing.assert_frame_equal(result, expected)

    # lambda syntax
    result = df.assign(C=lambda x: x.B / x.A).execute().fetch()
    expected = raw.assign(C=lambda x: x.B / x.A)
    pd.testing.assert_frame_equal(result, expected)

    # Non-Series array-like
    row_list = rs.rand(10).tolist()
    result = df.assign(C=row_list).execute().fetch()
    expected = raw.assign(C=row_list)
    pd.testing.assert_frame_equal(result, expected)

    # multiple
    row_list = rs.rand(10).tolist()
    result = df.assign(C=row_list, D=df.A, E=lambda x: x.B)
    result['C'] = result['C'].astype('int64')
    expected = raw.assign(C=row_list, D=raw.A, E=lambda x: x.B)
    expected['C'] = expected['C'].astype('int64')
    pd.testing.assert_frame_equal(result.execute().fetch(), expected)


def test_key_value(setup):
    raw = pd.DataFrame(np.random.rand(4, 3), columns=list('ABC'))
    df = DataFrame(raw)

    result = df.values.execute().fetch()
    np.testing.assert_array_equal(result, raw.values)

    result = df.keys().execute().fetch()
    pd.testing.assert_index_equal(result, raw.keys())

    raw = pd.Series(np.random.rand(10))
    s = Series(raw)

    result = s.values.execute().fetch()
    np.testing.assert_array_equal(result, raw.values)

    result = s.keys().execute().fetch()
    pd.testing.assert_index_equal(result, raw.keys())

    raw = pd.Index(np.random.rand(10))
    idx = Index(raw)

    result = idx.values.execute().fetch()
    np.testing.assert_array_equal(result, raw.values)


def test_between(setup):
    pd_series = pd.Series(pd.date_range("1/1/2000", periods=10))
    pd_left, pd_right = pd_series[2], pd_series[7]
    expected = pd_series.between(pd_left, pd_right)

    series = Series(pd_series, chunk_size=5)
    left, right = series[2], series[7]
    result = series.between(left, right).execute().fetch()
    pd.testing.assert_series_equal(result, expected)


def test_between_datetime_values(setup):
    pd_series = pd.Series(pd.bdate_range("1/1/2000", periods=20).astype(object))
    pd_series[::2] = np.nan
    expected = pd_series[3:18].dropna()

    series = Series(pd_series, chunk_size=5)
    result = series[series.between(series[3], series[17])]
    result = result.execute().fetch()
    pd.testing.assert_series_equal(result, expected)

    result = series[series.between(series[3], series[17], inclusive="neither")]
    result = result.execute().fetch()
    expected = pd_series[5:16].dropna()
    pd.testing.assert_series_equal(result, expected)


def test_between_period_values(setup):
    pd_series = pd.Series(pd.period_range("2000-01-01", periods=10, freq="D"))
    pd_left, pd_right = pd_series[2], pd_series[7]
    expected = pd_series.between(pd_left, pd_right)
    series = Series(pd_series, chunk_size=5)
    left, right = series[2], series[7]
    result = series.between(left, right).execute().fetch()
    pd.testing.assert_series_equal(result, expected)


def test_between_inclusive_string(setup):
    pd_series = pd.Series(pd.date_range("1/1/2000", periods=10))
    pd_left, pd_right = pd_series[2], pd_series[7]
    expected = pd_series.between(pd_left, pd_right)

    series = Series(pd_series, chunk_size=5)
    left, right = series[2], series[7]
    result = series.between(left, right, inclusive="both").execute().fetch()
    pd.testing.assert_series_equal(result, expected)

    result = series.between(left, right, inclusive="left").execute().fetch()
    expected = pd_series.between(pd_left, pd_right, inclusive="left")
    pd.testing.assert_series_equal(result, expected)

    result = series.between(left, right, inclusive="right").execute().fetch()
    expected = pd_series.between(pd_left, pd_right, inclusive="right")
    pd.testing.assert_series_equal(result, expected)

    result = series.between(left, right, inclusive="neither").execute().fetch()
    expected = pd_series.between(pd_left, pd_right, inclusive="neither")
    pd.testing.assert_series_equal(result, expected)


def test_between_error_args(setup):
    series = Series(pd.date_range("1/1/2000", periods=10), chunk_size=5)
    left, right = series[2], series[7]

    value_error_msg = (
        "Inclusive has to be either string of 'both',"
        "'left', 'right', or 'neither'."
    )

    with pytest.raises(ValueError, match=value_error_msg):
        series = Series(pd.date_range("1/1/2000", periods=10), chunk_size=5)
        series.between(left, right, inclusive="yes").execute().fetch()


def test_between_inclusive_warning(setup):
    pd_series = pd.Series(pd.date_range("1/1/2000", periods=10))
    series = Series(pd_series, chunk_size=5)
    left, right = series[2], series[7]

    with pytest.warns(FutureWarning):
        series.between(left, right, inclusive=False)
    with pytest.warns(FutureWarning):
        series.between(left, right, inclusive=True)
