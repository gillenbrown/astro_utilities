# note: modules are imported in each function to reduce overhead when using these utilities. This way, only the modules
# that are needed for the functions you use will be imported, rather than the modules needed for all utilities.

def reduced_chi_sq(model, data, errors):
    """ Does a reduced chi squared calculation

    .. math::
        \\chi^2 = \\sum_{k=1}^{n} \\left( \\frac{\\text{model}_k - \\text{data}_k}{\\text{error}_k} \\right) ^2

        \\chi^2_{\\text{red}} = \\frac{\\chi^2}{n}

    where :math:`n` is the number of data points.

    :param model: list of values that describe a possible fit to the data
    :param data: list of values that are the data do be fitted
    :param errors: list of errors on the data
    :return: value for the reduced chi squared value of the fit of the model to the data
    """
    if not len(model) == len(data) == len(errors):
        raise ValueError("The length of the model, data, and errors need to be the same.")
    chi_sq = 0
    for i in range(len(model)):
        chi_sq += ((model[i] - data[i])/errors[i])**2
    return chi_sq/(len(data))

def mag_to_flux(mag, zeropoint):
    """Convert a magnitude into a flux.

    We get the conversion by starting with the definition of the magnitude scale.

    .. math::
        m = -2.5 \\log_{10}(F) + C 

        2.5 \\log_{10}(F) = C - m

        F = 10^{\\frac{C-m}{2.5}}

    :param mag: magnitdue to be converted into a flux.
    :param zeropoint: zeropoint (in mags) of the magnitude system being used
    :return: flux that corresponds to the given magnitude
    """
    return 10**((zeropoint - mag)/2.5)


def flux_to_mag(flux, zeropoint):
    """Convert flux to magnitude with the given zeropoint.

    .. math::
        m = -2.5 \\log_{10} (F) + C

    :param flux: flux in whatever units. Choose your zeropoint correctly to make this work with the units flux is in.
    :param zeropoint: zeropoint of the system (in mags)
    :return: magnitude that corresponds to the given flux
    """
    import numpy as np
    try:
        return -2.5 * np.log10(flux) + zeropoint  # This is just the definition of magnitude
    except ValueError:  # the flux might be negative, and will mess things up
        return np.nan


def mag_errors_to_percent_flux_errors(mag_error):
    """Converts a magnitude error into a percent flux error.

    .. math::
        m = -2.5 \\log_{10} (F) + C

        dm = \\frac{-2.5}{\ln(10)} \\frac{dF}{F}

        \\frac{dF}{F} = \\frac{\\ln(10)}{2.5} dm 

    The minus sign just tells us that increasing flux gives decreasing magnitudes, so we can safely ignore it.

    note: :math:`ln(10) = 2.30258509299`
    I just plug in the numerical number to avoid importing things to take natural logs.

    :param mag_error: magnitude error
    :return: percentage flux error corresponding to this magnitude error.
    """
    return mag_error * (2.30258509299 / 2.5)  # math.log takes natural log unless specified.

def percent_flux_errors_to_mag_errors(percent_flux_error):
    """Converts a percentage flux error into a magnitude error.

    .. math::
        m = -2.5 \\log_{10} (F) + C

        dm = \\frac{-2.5}{\ln(10)} \\frac{dF}{F}

    note: :math:`ln(10) = 2.30258509299`
    I just plug in the numerical number to avoid importing things to take natural logs.

    :param percent_flux_error: percentage flux error
    :return: magnitude error corresponding to the percentage flux error.
    """
    return (2.5 / 2.30258509299) * percent_flux_error


def symmetric_match(table_1, table_2, ra_col_1="ra", ra_col_2="ra",
          dec_col_1="dec", dec_col_2="dec", max_sep=3.0):
    """
    Matches objects from two astropy tables by ra/dec.

    This function does symmetric matching. This measns that to be defined as
    a match, both objects must be each other's closest match. Their separation
    must also be less than the `max_sep` parameter.

    :param table_1: First astopy table object containing objects with ra/dec
                    information.
    :param table_2: First astopy table object containing objects with ra/dec
                    information.
    :param ra_col_1: Name of the ra column in table_1. Defaults to "ra".
    :param ra_col_2: Name of the ra column in table_2. Defaults to "ra".
    :param dec_col_1: Name of the dec column in table_1. Defaults to "dec".
    :param dec_col_2: Name of the dec column in table_2. Defaults to "dec".
    :param max_sep: Maximum separation (in arcseconds) allowed for two objects
                    to be considered a match.
    :return: Astropy table object containing the matches between the two
             input table objects. All columns from both catalogs will be
             included, as well as a separate separation column.
    """

    from astropy.coordinates import match_coordinates_sky, SkyCoord
    from astropy import units as u
    from astropy import table

    coords_1 = SkyCoord(table_1[ra_col_1], table_1[dec_col_1], unit=u.degree)
    coords_2 = SkyCoord(table_2[ra_col_2], table_2[dec_col_2], unit=u.degree)

    # find matches for objects in table 1 in table 2
    match_idx_12, sep_12, dist_12 = match_coordinates_sky(coords_1, coords_2)
    # and find matches for objects in table 2 in table 1
    match_idx_21, sep_21, dist_21 = match_coordinates_sky(coords_2, coords_1)

    # now check that the matching is symmetric
    symmetric_12 = []
    for idx_1, match_idx in enumerate(match_idx_12):
        if idx_1 == match_idx_21[match_idx] and sep_12[idx_1].arcsec < max_sep:
            symmetric_12.append((idx_1, match_idx, sep_12[idx_1].arcsec))

    idx_1, idx_2, sep = zip(*symmetric_12)

    idx_1 = list(idx_1)
    idx_2 = list(idx_2)
    sep = list(sep)

    # now turn into astropy table
    matches = table_1[idx_1]
    # get only the ones from table_2 that have matches
    matches_2 = table_2[idx_2]

    for col in matches_2.colnames:
        if col in matches.colnames:
            matches_2.rename_column(col, col + "_2")
            matches.add_column(matches_2[col + "_2"])
        else:
            matches.add_column(matches_2[col])

    matches.add_column(table.Column(data=sep, name="sep [arcsec]"))

    return matches


def empty_data(datatype):
    import numpy as np
    if "f" == datatype.kind:
        return np.nan
    elif "i" == datatype.kind:
        return -999999999999
    elif "S" == datatype.kind:
        return ""


def symmetric_match_both(table_1, table_2, ra_col_1="ra", ra_col_2="ra",
          dec_col_1="dec", dec_col_2="dec", max_sep=3.0):
    """
    Matches objects from two astropy tables by ra/dec, including all objects.

    This function does symmetric matching. This measns that to be defined as
    a match, both objects must be each other's closest match. Their separation
    must also be less than the `max_sep` parameter.

    Each object from both tables is included, even if there are no matches
    for that object. The empty space will be filled with the appropriate 
    empty data.

    :param table_1: First astopy table object containing objects with ra/dec
                    information.
    :param table_2: First astopy table object containing objects with ra/dec
                    information.
    :param ra_col_1: Name of the ra column in table_1. Defaults to "ra".
    :param ra_col_2: Name of the ra column in table_2. Defaults to "ra".
    :param dec_col_1: Name of the dec column in table_1. Defaults to "dec".
    :param dec_col_2: Name of the dec column in table_2. Defaults to "dec".
    :param max_sep: Maximum separation (in arcseconds) allowed for two objects
                    to be considered a match.
    :return: Astropy table object containing the matches between the two
             input table objects. All columns from both catalogs will be
             included, as well as a separate separation column.
    """

    from astropy.coordinates import match_coordinates_sky, SkyCoord
    from astropy import units as u
    from astropy import table
    import numpy as np

    coords_1 = SkyCoord(table_1[ra_col_1], table_1[dec_col_1], unit=u.degree)
    coords_2 = SkyCoord(table_2[ra_col_2], table_2[dec_col_2], unit=u.degree)

    # find matches for objects in table 1 in table 2
    match_idx_12, sep_12, dist_12 = match_coordinates_sky(coords_1, coords_2)
    # and find matches for objects in table 2 in table 1
    match_idx_21, sep_21, dist_21 = match_coordinates_sky(coords_2, coords_1)

    # now check that the matching is symmetric
    symmetric_12 = []
    for idx_1, match_idx in enumerate(match_idx_12):
        if idx_1 == match_idx_21[match_idx] and sep_12[idx_1].arcsec < max_sep:
            symmetric_12.append((idx_1, match_idx, sep_12[idx_1].arcsec))

    idx_1, idx_2, sep = zip(*symmetric_12)

    idx_1 = list(idx_1)
    idx_2 = list(idx_2)
    sep = list(sep)

    # now turn into astropy table
    matches = table_1[idx_1]
    # get only the ones from table_2 that have matches
    matches_2 = table_2[idx_2]

    for col in matches_2.colnames:
        if col in matches.colnames:
            matches_2.rename_column(col, col + "_2")
            matches.add_column(matches_2[col + "_2"])
        else:
            matches.add_column(matches_2[col])
            
    matches.add_column(table.Column(data=sep, name="sep [arcsec]"))
            
    # This adds all the matches. We need to add all the non-matches
    non_matches_1 = table_1.copy()
    non_matches_2 = table_2.copy()
    non_matches_1.remove_rows(idx_1)
    non_matches_2.remove_rows(idx_2)

    for row in non_matches_1:
        new_row = [item for item in row]
        for colname in matches.colnames[len(new_row):]:
            new_row.append(empty_data(matches[colname].dtype))
        matches.add_row(new_row)
    
    for row in non_matches_2:
        new_row = []
        for colname in matches.colnames[:len(non_matches_1.colnames)]:
            new_row.append(empty_data(matches[colname].dtype))
        for item in row:
            new_row.append(item)
            
        # add extra spot for separation
        new_row.append(np.nan)
            
        matches.add_row(new_row)


    return matches

def match_one(table_1, table_2, ra_col_1="ra", ra_col_2="ra",
          dec_col_1="dec", dec_col_2="dec", max_sep=3.0):
    """
    Matches objects from two astropy tables by ra/dec. All objects from the 
    first will be matched to one in the second. 


    :param table_1: First astopy table object containing objects with ra/dec
                    information.
    :param table_2: First astopy table object containing objects with ra/dec
                    information.
    :param ra_col_1: Name of the ra column in table_1. Defaults to "ra".
    :param ra_col_2: Name of the ra column in table_2. Defaults to "ra".
    :param dec_col_1: Name of the dec column in table_1. Defaults to "dec".
    :param dec_col_2: Name of the dec column in table_2. Defaults to "dec".
    :param max_sep: Maximum separation (in arcseconds) allowed for two objects
                    to be considered a match.
    :return: Astropy table object containing the matches between the two
             input table objects. All columns from both catalogs will be
             included, as well as a separate separation column.
    """

    from astropy.coordinates import match_coordinates_sky, SkyCoord
    from astropy import units as u
    from astropy import table
    import numpy as np

    coords_1 = SkyCoord(table_1[ra_col_1], table_1[dec_col_1], unit=u.degree)
    coords_2 = SkyCoord(table_2[ra_col_2], table_2[dec_col_2], unit=u.degree)
    
    

    # find matches for objects in table 1 in table 2
    match_idx_12, sep_12, dist_12 = match_coordinates_sky(coords_1, coords_2)
    # and find matches for objects in table 2 in table 1
    match_idx_21, sep_21, dist_21 = match_coordinates_sky(coords_2, coords_1)
    
    # get the matches that are close enough
    match_idx = match_idx_12[np.where(sep_12 < max_sep * u.arcsec)]
    sep = sep_12[np.where(sep_12 < max_sep * u.arcsec)]

    # now turn into astropy table
    matches = table_1[np.where(sep_12 < max_sep * u.arcsec)]
    # get only the ones from table_2 that have matches
    matches_2 = table_2[match_idx]

    for col in matches_2.colnames:
        if col in matches.colnames:
            matches_2.rename_column(col, col + "_2")
            matches.add_column(matches_2[col + "_2"])
        else:
            matches.add_column(matches_2[col])
            
    matches.add_column(table.Column(data=sep, name="sep [arcsec]"))

    return matches



def check_if_file(possible_location):
    """
    Check if a file already exists at a given location.

    :param possible_location: File to check. Can be a path to a file, too.
    :type possible_location: str
    :return: bool representing whether or not a file already exists there.
    """

    # have to do separate cases for files in current directory and those 
    # elsewhere. Those with paths has os.sep in their location.
    if os.sep in possible_location:
        # get all but the last part, which is the directory
        directory = os.sep.join(possible_location.split(os.sep)[:-1]) 
        # then the filename is what's left
        filename = possible_location.split(os.sep)[-1]
    else:  # it's in the current directory
        directory = "."
        filename = possible_location

    # Then check if the given file exists
    if filename in os.listdir(directory):
        return True 
    else:
        return False


def pretty_write(table, out_file, clobber=False):
    """
    Writes an astropy table in a nice format.

    :param table: Astropy table object to write to file.
    :type table: astropy.table.Table
    :param out_file: Place to write the resulting ascii file. 
    :type out_file: str
    :param clobber: Whether or not to overwrite an existing file, if it exists.
                    If this is false, the function will exit with an error if
                    a file already exists here. If clobber is True, it will
                    overwrite the file there.
    :type clobber: bool

    """
    # first check if a file exists there, and raise an error if it does.
    if not clobber:
        if check_if_file(out_file):
            raise IOError("File already exists. "
                          "Set `clobber=True` if you want to overwrite. ")
    # will continue if no error is raised.
    
    with open(out_file, "w") as output:
        # set an empty string that defines how the formatting will work, that
        # we will add to as we go
        formatting = ""
        first = True # have to keep track of the first one

        # then use the column names and data within to determine the width each
        # column will need when written to a file, and put that info in the
        # formatter variable
        for col in table.colnames:
            # find the maximum length of either the column name of the
            # data in that column. For data, get the length of the string
            # representation of the object, since that's what will be
            # written to the file
            max_data_len = max([len(str(item)) for item in table[col]])
            max_len = max(max_data_len, len(col))
            max_len += 5  # add 5 to make it spread out nicer
            
            # if it's the first one, add extra for the comment
            if first:
                max_len += 2
                first = False
            
            # use this info to add the next part of the formatter
            # the double braces are so we can get actual braces, then the 
            # length goes after the "<"
            formatting += "{{:<{}}}".format(max_len)

        # we are now done with the formatting string, so add a newline
        formatting += "\n"
        
        # Now write the header column
        colnames = table.colnames
        # add a comment to the first one
        colnames[0] = "# " + colnames[0]
        output.write(formatting.format(*colnames))
        
        # then write all the data
        for line in table:
            output.write(formatting.format(*line))
            
#TODO: write wrappers for the astropy join stuff

# Note: these all need to be tested.

