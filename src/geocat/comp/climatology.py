import xarray as xr
import cf_xarray
import numpy as np
import typing

xr.set_options(keep_attrs=True)

_FREQUENCIES = {"day", "month", "year", "season"}


def _find_time_invariant_vars(dset, time_coord_name):
    if isinstance(dset, xr.Dataset):
        return [
            v for v in dset.variables if time_coord_name not in dset[v].dims
        ]
    return


def _contains_datetime_like_objects(d_arr):
    """Check if a variable contains datetime like objects (either
    np.datetime64, or cftime.datetime)
    """
    return np.issubdtype(
        d_arr.dtype,
        np.datetime64) or xr.core.common.contains_cftime_datetimes(d_arr)


def _validate_freq(freq):
    if freq not in _FREQUENCIES:
        raise ValueError(
            f"{freq} is not among supported frequency aliases={list(_FREQUENCIES)}"
        )


def _get_time_coordinate_info(dset, time_coord_name):
    if time_coord_name:
        time = dset[time_coord_name]
    else:
        time = dset.cf["time"]
        time_coord_name = time.name

    if not _contains_datetime_like_objects(time):
        raise ValueError(
            f"The {time_coord_name} coordinate should be either `np.datetime64` or `cftime.datetime`"
        )

    return time_coord_name


def _setup_clim_anom_input(dset, freq, time_coord_name):
    _validate_freq(freq)

    time_coord_name = _get_time_coordinate_info(dset, time_coord_name)
    time_invariant_vars = _find_time_invariant_vars(dset, time_coord_name)
    if time_invariant_vars:
        data = dset.drop_vars(time_invariant_vars)
    else:
        data = dset
    time_dot_freq = ".".join([time_coord_name, freq])

    return data, time_invariant_vars, time_coord_name, time_dot_freq


def climatology(
        dset: typing.Union[xr.DataArray, xr.Dataset],
        freq: str,
        time_coord_name: str = None) -> typing.Union[xr.DataArray, xr.Dataset]:
    """Compute climatologies for a specified time frequency.

    Parameters
    ----------
    dset : xr.Dataset, xr.DataArray
        The data on which to operate

    freq : str
        Climatology frequency alias. Accepted alias:

            - 'day': for daily climatologies
            - 'month': for monthly climatologies
            - 'year': for annual climatologies
            - 'season': for seasonal climatologies

    time_coord_name: str, Optional
         Name for time coordinate to use

    Returns
    -------
    computed_dset : xr.Dataset, xr.DataArray
       The computed climatology data

    Examples
    --------
    >>> import xarray as xr
    >>> import pandas as pd
    >>> import numpy as np
    >>> import geocat.comp
    >>> dates = pd.date_range(start="2000/01/01", freq="M", periods=24)
    >>> ts = xr.DataArray(np.arange(24).reshape(24, 1, 1), dims=["time", "lat", "lon"], coords={"time": dates})
    >>> ts
    <xarray.DataArray (time: 24, lat: 1, lon: 1)>
    array([[[ 0]],

        [[ 1]],

        [[ 2]],
    ...
        [[21]],

        [[22]],

        [[23]]])
    Coordinates:
    * time     (time) datetime64[ns] 2000-01-31 2000-02-29 ... 2001-12-31
    Dimensions without coordinates: lat, lon
    >>> geocat.comp.climatology(ts, 'year')
    <xarray.DataArray (year: 2, lat: 1, lon: 1)>
    array([[[ 5.5]],

        [[17.5]]])
    Coordinates:
    * year     (year) int64 2000 2001
    Dimensions without coordinates: lat, lon
    >>> geocat.comp.climatology(ts, 'season')
    <xarray.DataArray (season: 4, lat: 1, lon: 1)>
    array([[[10.]],

        [[12.]],

        [[ 9.]],

        [[15.]]])
    Coordinates:
    * season   (season) object 'DJF' 'JJA' 'MAM' 'SON'
    Dimensions without coordinates: lat, lon
    """
    data, time_invariant_vars, time_coord_name, time_dot_freq = _setup_clim_anom_input(
        dset, freq, time_coord_name)

    grouped = data.groupby(time_dot_freq)
    # TODO: Compute weighted climatologies when `time_bounds` are available
    clim = grouped.mean(time_coord_name)
    if time_invariant_vars:
        return xr.concat([dset[time_invariant_vars], clim], dim=time_coord_name)
    else:
        return clim


def anomaly(
        dset: typing.Union[xr.DataArray, xr.Dataset],
        freq: str,
        time_coord_name: str = None) -> typing.Union[xr.DataArray, xr.Dataset]:
    """Compute anomalies for a specified time frequency.

    Parameters
    ----------
    dset : xr.Dataset, xr.DataArray
        The data on which to operate

    freq : str
        Anomaly frequency alias. Accepted alias:

            - 'day': for daily anomalies
            - 'month': for monthly anomalies
            - 'year': for annual anomalies
            - 'season': for seasonal anomalies

    time_coord_name: str, Optional
         Name for time coordinate to use

    Returns
    -------
    computed_dset : xr.Dataset, xr.DataArray
       The computed anomaly data

    Examples
    --------
    >>> import xarray as xr
    >>> import pandas as pd
    >>> import numpy as np
    >>> import geocat.comp
    >>> dates = pd.date_range(start="2000/01/01", freq="M", periods=24)
    >>> ts = xr.DataArray(np.arange(24).reshape(24, 1, 1), dims=["time", "lat", "lon"], coords={"time": dates})
    >>> ts
    <xarray.DataArray (time: 24, lat: 1, lon: 1)>
    array([[[ 0]],

        [[ 1]],

        [[ 2]],

    ...

        [[21]],

        [[22]],

        [[23]]])
    Coordinates:
    * time     (time) datetime64[ns] 2000-01-31 2000-02-29 ... 2001-12-31
    Dimensions without coordinates: lat, lon
    >>> geocat.comp.anomaly(ts, 'season')
    <xarray.DataArray (time: 24, lat: 1, lon: 1)>
    array([[[-10.]],

        [[ -9.]],

        [[ -7.]],

    ...

        [[  6.]],

        [[  7.]],

        [[ 13.]]])
    Coordinates:
    * time     (time) datetime64[ns] 2000-01-31 2000-02-29 ... 2001-12-31
        season   (time) <U3 'DJF' 'DJF' 'MAM' 'MAM' ... 'SON' 'SON' 'SON' 'DJF'
    Dimensions without coordinates: lat, lon
    """

    data, time_invariant_vars, time_coord_name, time_dot_freq = _setup_clim_anom_input(
        dset, freq, time_coord_name)

    clim = climatology(data, freq, time_coord_name)
    anom = data.groupby(time_dot_freq) - clim
    if time_invariant_vars:
        return xr.merge([dset[time_invariant_vars], anom])
    else:
        return anom


def month_to_season(
    dset: typing.Union[xr.Dataset, xr.DataArray],
    season: str,
    time_coord_name: str = None,
) -> typing.Union[xr.Dataset, xr.DataArray]:
    """Computes a user-specified three-month seasonal mean.

    This function takes an xarray dataset containing monthly data spanning years and
    returns a dataset with one sample per year, for a specified three-month season.

    Parameters
    ----------
    dset : xr.Dataset, xr.DataArray
        The data on which to operate
    season : str
        A string representing the season to calculate: e.g., "JFM", "JJA".
        Valid values are:

         - DJF
         - JFM
         - FMA
         - MAM
         - AMJ
         - MJJ
         - JJA
         - JAS
         - ASO
         - SON
         - OND
         - NDJ
    time_coord_name: str, Optional
        Name for time coordinate to use

    Returns
    -------
    computed_dset : xr.Dataset, xr.DataArray
       The computed data

    Notes
    -----
    This function requires the number of months to be a multiple of 12, i.e. full years must be provided.
    Time stamps are centered on the season. For example, seasons='DJF' returns January timestamps.
    If a calculated season's timestamp falls outside the original range of monthly values, then the calculated mean
    is dropped.  For example, if the monthly data's time range is [Jan-2000, Dec-2003] and the season is "DJF", the
    seasonal mean computed from the single month of Dec-2003 is dropped.
    """

    time_coord_name = _get_time_coordinate_info(dset, time_coord_name)
    mod = 12
    if dset[time_coord_name].size % mod != 0:
        raise ValueError(
            f"The {time_coord_name} axis length must be a multiple of {mod}.")

    seasons_pd = {
        "DJF": ("QS-DEC", 1),
        "JFM": ("QS-JAN", 2),
        "FMA": ("QS-FEB", 3),
        "MAM": ("QS-MAR", 4),
        "AMJ": ("QS-APR", 5),
        "MJJ": ("QS-MAY", 6),
        "JJA": ("QS-JUN", 7),
        "JAS": ("QS-JUL", 8),
        "ASO": ("QS-AUG", 9),
        "SON": ("QS-SEP", 10),
        "OND": ("QS-OCT", 11),
        "NDJ": ("QS-NOV", 12),
    }
    try:
        (season_pd, season_sel) = seasons_pd[season]
    except KeyError:
        raise KeyError(
            f"contributed: month_to_season: bad season: SEASON = {season}. Valid seasons include: {list(seasons_pd.keys())}"
        )

    start_date = dset[time_coord_name][0]
    end_date = dset[time_coord_name][-1]

    # Compute the three-month means, moving time labels ahead to the middle
    # month.
    month_offset = "MS"
    dset_seasons = dset.resample({
        time_coord_name: season_pd
    },
                                 loffset=month_offset).mean()

    # Filter just the desired season, and trim to the desired time range.
    compute_dset = dset_seasons.sel({
        time_coord_name: dset_seasons[time_coord_name].dt.month == season_sel
    }).sel({time_coord_name: slice(start_date, end_date)})
    return compute_dset
