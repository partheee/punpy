"""Use Monte Carlo to propagate uncertainties"""

import comet_maths as cm
import numpy as np

"""___Authorship___"""
__author__ = "Pieter De Vis"
__created__ = "30/03/2019"
__maintainer__ = "Pieter De Vis"
__email__ = "pieter.de.vis@npl.co.uk"
__status__ = "Development"


class MeasurementFunctionUtils:
    def __init__(self, xvariables, ydims, str_repeat_corr_dims, verbose, templ, use_err_corr_dict):
        """
        Initialise MeasurementFunctionUtils

        :param xvariables: list of input quantity names, in same order as arguments in measurement function and with same exact names as provided in input datasets.
        :type xvariables: list(str)
        :param str_repeat_corr_dims: list of dimension names to be used as repeated dims
        :type str_repeat_corr_dims: list(str)
        :param verbose: boolean to set verbosity
        :type verbose: bool
        :param templ: templater object
        :type templ: punpy.digital_effects_table_template
        """
        self.xvariables = xvariables
        self.verbose = verbose
        self.ydims = ydims
        self.str_repeat_corr_dims = str_repeat_corr_dims
        self.templ = templ
        self.repeat_dims_form = "structured"
        self.use_err_corr_dict = use_err_corr_dict

    def find_repeat_dim_corr(self, form, *args, store_unc_percent=False, ydims=None):
        """
        Function to make dict with the error correlation information along the repeated dims.

        :param form: name or type of uncertainty component
        :type form: str
        :param args: One or multiple digital effects tables with input quantities, defined with obsarray
        :type args: obsarray dataset(s)
        :param store_unc_percent: Boolean defining whether relative uncertainties should be returned or not. Default to True (relative uncertaintie returned)
        :type store_unc_percent: bool (optional)
        :return: dictionary with errcorr info for repeated dims
        :rtype: dict
        """
        repeat_dims_errcorrs = {}
        for repeat_dim in self.ydims:
            if repeat_dim in self.str_repeat_corr_dims:
                repeat_dims_errcorrs[repeat_dim] = {
                    "dim": repeat_dim,
                    "form": None,
                    "params": [],
                    "units": [],
                }
                for iv, var in enumerate(self.xvariables):
                    for dataset in args:
                        if hasattr(dataset, "variables"):
                            if var in dataset.variables:
                                comps = self.find_comps(
                                    form,
                                    dataset,
                                    var,
                                    store_unc_percent=store_unc_percent,
                                    ydims=ydims,
                                )
                                if comps is None:
                                    continue
                                elif len(comps) == 0:
                                    continue
                                elif repeat_dim in dataset[var].dims:
                                    repeat_dims_errcorrs = (
                                        self.set_repeat_dims_errcorrs(
                                            comps,
                                            dataset,
                                            var,
                                            repeat_dim,
                                            repeat_dims_errcorrs,
                                        )
                                    )
                                else:
                                    self.check_repeat_err_corr_same(
                                        repeat_dims_errcorrs[repeat_dim], "systematic"
                                    )
                                    repeat_dims_errcorrs[repeat_dim][
                                        "form"
                                    ] = "systematic"
        return repeat_dims_errcorrs

    def set_repeat_dims_errcorrs(
        self, comps, dataset, var, repeat_dim, repeat_dims_errcorrs
    ):
        for comp in comps:
            for idim in range(len(dataset[var].dims)):
                if dataset[comp].attrs["err_corr_%s_dim" % (idim + 1)] == repeat_dim:
                    self.check_repeat_err_corr_same(
                        repeat_dims_errcorrs[repeat_dim],
                        dataset[comp],
                        idim,
                    )
                    repeat_dims_errcorrs[repeat_dim]["form"] = dataset[comp].attrs[
                        "err_corr_%s_form" % (idim + 1)
                    ]
                    repeat_dims_errcorrs[repeat_dim]["params"] = dataset[comp].attrs[
                        "err_corr_%s_params" % (idim + 1)
                    ]
                    repeat_dims_errcorrs[repeat_dim]["units"] = dataset[comp].attrs[
                        "err_corr_%s_units" % (idim + 1)
                    ]

        return repeat_dims_errcorrs

    def check_repeat_err_corr_same(self, repeat_dims_errcorr, uvar, idim=None):
        """
        Function to check whether the err_corr along the repeated dim for specific uncertainty variable is the same as the current errcorr dictionary.

        :param repeat_dims_errcorr: dictionary with errcorr info for repeated dims
        :type repeat_dims_errcorr: dict
        :param uvar: Uncertainty variable to check
        :type uvar: xarray.dataarray
        :param idim: index of the current dimension. Defaults to None.
        :type idim: int
        :return: None
        :rtype: None
        """
        if repeat_dims_errcorr["form"] is None:
            pass

        elif isinstance(uvar, str):
            if repeat_dims_errcorr["form"] == uvar:
                pass
            else:
                raise ValueError(
                    "punpy.measurement_function: Not all included uncertainty contributions have the same error correlation along the repeat_dims. Either don't use repeat_dims or use a different method, where components are propagated seperately."
                )
        else:
            if (
                (
                    repeat_dims_errcorr["form"]
                    == uvar.attrs["err_corr_%s_form" % (idim + 1)]
                )
                and (
                    repeat_dims_errcorr["params"]
                    == uvar.attrs["err_corr_%s_params" % (idim + 1)]
                )
                and (
                    repeat_dims_errcorr["units"]
                    == uvar.attrs["err_corr_%s_units" % (idim + 1)]
                )
            ):
                pass
            else:
                raise ValueError(
                    "punpy.measurement_function: Not all included uncertainty contributions have the same error correlation along the repeat_dims. Either don't use repeat_dims or use a different method, where components are propagated seperately."
                )

    def set_repeat_dims_form(self, repeat_dims_errcorrs):
        """
        Function to set self.repeat_dims_form to the correct form.

        :param repeat_dims_errcorrs: dictionary with errcorr info for repeated dims
        :type repeat_dims_errcorrs: dict
        :return: None
        :rtype: None
        """
        try:
            if len(self.str_repeat_corr_dims) == 0 or len(repeat_dims_errcorrs) == 0:
                self.repeat_dims_form = "None"

            elif np.all(
                [
                    repeat_dims_errcorrs[repeat_dim]["form"] == "random"
                    for repeat_dim in self.str_repeat_corr_dims
                ]
            ):
                self.repeat_dims_form = "random"

            elif np.all(
                [
                    repeat_dims_errcorrs[repeat_dim]["form"] == "systematic"
                    for repeat_dim in self.str_repeat_corr_dims
                ]
            ):
                self.repeat_dims_form = "systematic"

            else:
                self.repeat_dims_form = "structured"
        except:
            if np.all(
                [
                    repeat_dims_errcorrs[0][repeat_dim]["form"] == "random"
                    for repeat_dim in self.str_repeat_corr_dims
                ]
            ):
                self.repeat_dims_form = "random"

            elif np.all(
                [
                    repeat_dims_errcorrs[0][repeat_dim]["form"] == "systematic"
                    for repeat_dim in self.str_repeat_corr_dims
                ]
            ):
                self.repeat_dims_form = "systematic"

            else:
                self.repeat_dims_form = "structured"

    def find_comps(self, form, dataset, var, store_unc_percent=False, ydims=None):
        """
        Function to find the components corresponding to provided uncertainty form (name or type).

        :param form: name or type of uncertainty component
        :type form: str
        :param dataset: dataset being querried
        :type dataset: xarray.dataset
        :param var: variable for which uncertainty components are being listed.
        :type var: str
        :param store_unc_percent: Boolean defining whether relative uncertainties should be returned or not. Default to True (relative uncertaintie returned)
        :type store_unc_percent: bool (optional)
        :param ydims: list of dimensions of the measurand, in correct order.
        :type ydims: list(str)
        :return: list of names of uncertainty components
        :rtype: list(str)
        """
        comps = dataset.unc[var].comps
        if comps is None:
            pass
        elif form == "tot":
            comps = list(comps.variables.mapping.keys())
        elif form == "ran" or form == "random":
            comps = dataset.unc[var].random_comps
            if comps is not None:
                comps = list(comps.variables.mapping.keys())
            if len(dataset[var].dims) < len(ydims):
                comps = []
        elif form == "sys" or form == "systematic":
            comps = dataset.unc[var].systematic_comps
            if comps is not None:
                comps = list(comps.variables.mapping.keys())
        elif form == "str":
            comps = dataset.unc[var].structured_comps
            if comps is not None:
                comps = list(comps.variables.mapping.keys())
            else:
                comps = []
            if len(dataset[var].dims) < len(ydims):
                comps_rand = dataset.unc[var].random_comps
                if comps_rand is not None:
                    comps.append(*list(comps_rand.variables.mapping.keys()))

        else:
            compname = self.templ.make_ucomp_name(
                form, store_unc_percent=store_unc_percent, var=var
            )
            if compname in comps:
                comps = [compname]
            else:
                comps = []
        return comps

    def get_input_qty(self, *args, ydims=None, sizes_dict=None, expand=False):
        """
        Function to extract input quantities from datasets and return as list of arrays.

        :param args: One or multiple digital effects tables with input quantities, defined with obsarray
        :type args: obsarray dataset(s)
        :param ydims: list of dimensions of the measurand, in correct order.
        :type ydims: list(str)
        :param sizes_dict: Dictionary with sizes of each of the dimensions of the measurand.
        :type sizes_dict: dict
        :param expand: boolean to indicate whether the input quantities should be expanded/broadcasted to the shape of the measurand.
        :type expand: bool
        :return: list of values (as np.ndarray) for each of the input quantites.
        :rtype: list(np.ndarray)
        """
        if len(self.xvariables) == 0:
            raise ValueError("Variables have not been specified.")

        if expand:
            if sizes_dict is None:
                raise ValueError("sizes_dict should be set when using expand.")
            if ydims is None:
                raise ValueError("ydims should be set when using expand.")
            datashape = [sizes_dict[dim] for dim in ydims]

        inputs = np.empty(len(self.xvariables), dtype=object)
        for iv, var in enumerate(self.xvariables):
            found = False
            for dataset in args[0]:
                if hasattr(dataset, "variables"):
                    if var in dataset.variables:
                        inputs[iv] = dataset[var].values
                        found = True
                        if expand:
                            if inputs[iv].shape != datashape:
                                add_dims = [
                                    dim for dim in ydims if dim not in dataset[var].dims
                                ]
                                for dim in add_dims:
                                    tileshape = np.ones(len(ydims), dtype=int)
                                    if len(inputs[iv].shape) != len(datashape):
                                        tileshape[0] = sizes_dict[dim]
                                        inputs[iv] = np.tile(inputs[iv], tileshape)
                                        for idim2, dim2 in enumerate(add_dims):
                                            inputs[iv] = np.moveaxis(
                                                inputs[iv], idim2, ydims.index(dim2)
                                            )
                                    else:
                                        tileshape[ydims.index(dim)] = sizes_dict[dim]
                                        inputs[iv] = np.tile(inputs[iv], tileshape)
                elif var in dataset.keys():
                    inputs[iv] = dataset[var]
                    found = True

            if not found:
                raise ValueError("Variable %s not found in provided datasets." % (var))

        return inputs

    def get_input_unc(self, form, *args, ydims=None, sizes_dict=None, expand=False):
        """
        Function to extract uncertainties on the input quantities from datasets and return as list of arrays.

        :param form: name or type of uncertainty component
        :type form: str
        :param args: One or multiple digital effects tables with input quantities, defined with obsarray
        :type args: obsarray dataset(s)
        :param ydims: list of dimensions of the measurand, in correct order.
        :type ydims: list(str)
        :param sizes_dict: Dictionary with sizes of each of the dimensions of the measurand.
        :type sizes_dict: dict
        :param expand: boolean to indicate whether the input quantities should be expanded/broadcasted to the shape of the measurand.
        :type expand: bool
        :return: list of uncertainty values (as np.ndarray) for each of the input quantites.
        :rtype: list(np.ndarray)
        """
        inputs_unc = np.empty(len(self.xvariables), dtype=object)
        for iv, var in enumerate(self.xvariables):
            inputs_unc[iv] = None
            for dataset in args[0]:
                if hasattr(dataset, "variables"):
                    if var in dataset.variables:
                        if ydims is not None:
                            if np.all([dim in dataset[var].dims for dim in ydims]):
                                inputs_unc[iv] = self.calculate_unc(form, dataset, var)

                            else:
                                inputs_unc[iv] = self.calculate_unc_missingdim(
                                    form,
                                    dataset,
                                    var,
                                    expand=expand,
                                    sizes_dict=sizes_dict,
                                    ydims=ydims,
                                )

            if np.count_nonzero(inputs_unc[iv]) == 0:
                inputs_unc[iv] = None
            if inputs_unc[iv] is None:
                if self.verbose:
                    print(
                        "%s uncertainty for variable %s not found in provided datasets. Zero uncertainty assumed."
                        % (form, var)
                    )
        return inputs_unc

    def calculate_unc(self, form, ds, var):
        """
        Function to extract uncertainties of given form on given variable from the given datasets and return as array.

        :param form: name or type of given uncertainty component
        :type form: str
        :param ds: given dataset
        :type ds: xarray.dataset
        :param var: given variable
        :type var: str
        :return: uncertainty values for the given variable in the given dataset. returns None if uncertainty component is not present in dataset.
        :rtype: np.ndarray
        """
        if form == "tot":
            data = ds.unc[var].total_unc()
        elif form == "rand":
            data = ds.unc[var].random_unc()
        elif form == "syst":
            data = ds.unc[var].systematic_unc()
        elif form == "stru":
            data = ds.unc[var].structured_unc()
        else:
            try:
                uvar = "%s_%s" % (form, var)
                data = ds[uvar]
                if data.attrs["units"] == "%":
                    return data.values / 100 * ds[var].values
            except:
                keys = np.array(list(ds.keys()))
                uvar_ids = [
                    ("_%s_%s" % (form, var) in key) and (key[0] == "u") for key in keys
                ]
                uvar = keys[uvar_ids]

                if len(uvar) > 0:
                    data = ds[uvar[0]]
                    if data.attrs["units"] == "%":
                        return data.values / 100 * ds[var].values
                    else:
                        return data.values
                else:
                    data = None

        if data is not None:
            return data.values

    def calculate_unc_missingdim(
        self, form, ds, var, ydims=None, sizes_dict=None, expand=False
    ):
        """
        Function to extract uncertainties of given form on given variable from the given datasets when there are missing dimensions.
        With missing dimension, we here mean a dimension that is present in the measurand, but not in the input quantity being considered.

        :param form: name or type of uncertainty component
        :type form: str
        :param ds: given dataset
        :type ds: xarray.dataset
        :param var: given variable
        :type var: str
        :param ydims: list of dimensions of the measurand, in correct order.
        :type ydims: list(str)
        :param sizes_dict: Dictionary with sizes of each of the dimensions of the measurand.
        :type sizes_dict: dict
        :param expand: boolean to indicate whether the input quantities should be expanded/broadcasted to the shape of the measurand.
        :type expand: bool
        :return: uncertainty values for the given variable in the given dataset. returns None if uncertainty component is not present in dataset.
        :rtype: np.ndarray
        """
        if expand:
            if sizes_dict is None:
                raise ValueError("sizes_dict should be set when using expand.")
            if ydims is None:
                raise ValueError("ydims should be set when using expand.")
            datashape = [sizes_dict[dim] for dim in ydims]

        if (form == "rand") and (self.repeat_dims_form != "random"):
            out = None
        elif (form == "syst") and (self.repeat_dims_form != "systematic"):
            out = None
        elif form == "stru":
            ustru = self.calculate_unc("stru", ds, var)
            if self.repeat_dims_form != "random":
                urand = self.calculate_unc("rand", ds, var)
            else:
                urand = None
            if self.repeat_dims_form != "systematic":
                usyst = self.calculate_unc("syst", ds, var)
            else:
                usyst = None

            out = [ucomp ** 2 for ucomp in [ustru, urand, usyst] if ucomp is not None]

            out = np.sum(out, axis=0) ** 0.5
        else:
            out = self.calculate_unc(form, ds, var)

        if expand and (out is not None):
            add_dims = [dim for dim in ydims if dim not in ds[var].dims]
            for dim in add_dims:
                tileshape = np.ones(len(ydims), dtype=int)
                if len(out.shape) != len(datashape):
                    tileshape[0] = sizes_dict[dim]
                    out = np.moveaxis(np.tile(out, tileshape), 0, ydims.index(dim))
                else:
                    tileshape[ydims.index(dim)] = sizes_dict[dim]
                    out = np.tile(out, tileshape)
        return out

    def get_input_corr(self, form, *args, ydims=None, sizes_dict=None, expand=False):
        """
        Function to extract error-correlation matrices for the input quantities from datasets and return as list of arrays.

        :param form: name or type of uncertainty component
        :type form: str
        :param args: One or multiple digital effects tables with input quantities, defined with obsarray
        :type args: obsarray dataset(s)
        :param ydims: list of dimensions of the measurand, in correct order.
        :type ydims: list(str)
        :param sizes_dict: Dictionary with sizes of each of the dimensions of the measurand.
        :type sizes_dict: dict
        :param expand: boolean to indicate whether the input quantities should be expanded/broadcasted to the shape of the measurand.
        :type expand: bool
        :return: list of error-correlation matrix values (as np.ndarray) for each of the input quantities.
        :rtype: list(np.ndarray)
        """
        inputs_corr = np.empty(len(self.xvariables), dtype=object)
        for iv, var in enumerate(self.xvariables):
            inputs_corr[iv] = None
            for dataset in args[0]:
                if hasattr(dataset, "variables"):
                    if var in dataset.variables:
                        if len(dataset[var].dims) < len(ydims):
                            inputs_corr[iv] = self.calculate_corr_missingdim(
                                form,
                                dataset,
                                var,
                                expand=expand,
                                sizes_dict=sizes_dict,
                                ydims=ydims,
                            )
                        else:
                            inputs_corr[iv] = self.calculate_corr(form, dataset, var)
            if inputs_corr[iv] is None:
                if self.verbose:
                    print(
                        "%s error-correlation for variable %s not found in provided datasets."
                        % (form, var)
                    )

        return inputs_corr

    def calculate_corr(self, form, ds, var):
        """
        Function to extract error-correlation matrices of given form on given variable from the given datasets and return as array.

        :param form: name or type of given uncertainty component
        :type form: str
        :param ds: given dataset
        :type ds: xarray.dataset
        :param var: given variable
        :type var: str
        :return: error-correlation matrix values for the given variable in the given dataset. returns None if uncertainty component is not present in dataset.
        :rtype: np.ndarray
        """
        sli = list([slice(None)] * ds[var].ndim)
        var_dims = ds[var].dims
        for i in range(len(sli)):
            if var_dims[i] in self.str_repeat_corr_dims:
                sli[i] = 0
        dsu = ds.unc[var][tuple(sli)]
        if form == "tot":
            return dsu.total_err_corr_matrix().values
        elif form == "stru":
            return dsu.structured_err_corr_matrix().values
        elif form == "rand":
            return "rand"
        elif form == "syst":
            return "syst"
        else:
            try:
                uvar = "%s_%s" % (form, var)
                data = ds[uvar]
            except:
                keys = np.array(list(ds.keys()))
                uvar_ids = [
                    ("_%s_%s" % (form, var) in key) and (key[0] == "u") for key in keys
                ]
                uvar = keys[uvar_ids]
                if len(uvar) > 0:
                    data = ds[uvar[0]]
                else:
                    data = None

            try:
                uvar = "%s_%s" % (form, var)
                if self.use_err_corr_dict:
                    return dsu[uvar].err_corr_dict_numdim()
                else:
                    return dsu[uvar].err_corr_matrix().values
            except:
                keys = np.array(list(ds.keys()))
                uvar_ids = [
                    ("_%s_%s" % (form, var) in key) and (key[0] == "u") for key in keys
                ]
                uvar = keys[uvar_ids]
                if len(uvar) > 0:
                    if self.use_err_corr_dict:
                        return dsu[uvar[0]].err_corr_dict_numdim()
                    else:
                        return dsu[uvar[0]].err_corr_matrix().values
                else:
                    return None

    def calculate_corr_missingdim(
        self, form, ds, var, ydims=None, sizes_dict=None, expand=False
    ):
        """
        Function to extract error-correlation matrices of given form on given variable from the given datasets when there are missing dimensions.
        With missing dimension, we here mean a dimension that is present in the measurand, but not in the input quantity being considered.

        :param form: name or type of uncertainty component
        :type form: str
        :param ds: given dataset
        :type ds: xarray.dataset
        :param var: given variable
        :type var: str
        :param ydims: list of dimensions of the measurand, in correct order.
        :type ydims: list(str)
        :param sizes_dict: Dictionary with sizes of each of the dimensions of the measurand.
        :type sizes_dict: dict
        :param expand: boolean to indicate whether the input quantities should be expanded/broadcasted to the shape of the measurand.
        :type expand: bool
        :return: error-correlation matrix values for the given variable in the given dataset. returns None if uncertainty component is not present in dataset.
        :rtype: np.ndarray
        """
        sli = [
            slice(None) if (ydim not in self.str_repeat_corr_dims) else 0
            for ydim in ds[var].dims
        ]
        dsu = ds.unc[var][tuple(sli)]
        vardims = [
            ydim for ydim in ds[var].dims if (ydim not in self.str_repeat_corr_dims)
        ]

        outdims = [ydim for ydim in ydims if ydim not in self.str_repeat_corr_dims]
        missingdims = [
            ydim
            for ydim in ydims
            if ((ydim not in ds[var].dims) and (ydim not in self.str_repeat_corr_dims))
        ]

        missingshape = [sizes_dict[dim] for dim in missingdims]
        missinglen = np.prod(missingshape)

        if form == "rand":
            return None
        elif form == "stru":
            cov_stru = dsu.structured_err_cov_matrix()
            unc_rand = dsu.random_unc()
            if unc_rand is None:
                out = cm.correlation_from_covariance(cov_stru.values)
            else:
                corr_rand = np.eye(np.prod(unc_rand.shape))
                if cov_stru is None:
                    out = corr_rand
                else:
                    cov_rand = cm.convert_corr_to_cov(corr_rand, unc_rand.values)
                    out = cm.correlation_from_covariance(cov_stru.values + cov_rand)

        else:
            out = self.calculate_corr(form, ds, var)

        if expand and (out is not None):
            out_1 = cm.expand_errcorr_dims(out, vardims, outdims, sizes_dict)
            out_2 = cm.expand_errcorr_dims(
                np.ones((missinglen, missinglen)), missingdims, outdims, sizes_dict
            )
            out = out_1.dot(out_2)

        return out
