## Synopsis

This application reproduces the Debian _partman_ algorithm (as found here:
<https://anonscm.debian.org/cgit/d-i/partman-auto.git/tree/lib/recipes.sh>),
and via a standard set of form inputs, can be used to visualize probable disk
partitioning or to generate a _partman_ recipe proper.

## Motivation

It was with considerable frustration that the author discovered that what's in
a _partman_ recipe isn't always what ends up on disk; there is an older tool in
the Debian Wiki called _PartmanPRC_, but it has some limitations, like not
properly handling '-1' in an input field, being overly rigid about how the
application runs, and generally being kind of old. This application uses PyGal
to generate SVG diagrams in a browser window, or to generate _partman_ recipes
in plaintext that can be saved and used with a _preseed_ install script.

## Installation

This application should run as a regular WSGI app under Passenger, or as a
standalone application. Simply install the requirements using _pip_, and go.

## Tests

There are some sample inputs included within the `__main__` section of the
application itself; simply run `python ./partman_calc.py` and it will convert
the sample inputs to processed outputs and display the results.

### Test output

The output consists of a two-element list for each disk partition; the first
element of the list contains the partition name, and the second element is a
list containing the partition's minimum size, calculated priority, and maximum
size. Any input values containing a percent sign will be converted to integers
with values relative to RAM available. Free disk space is assumed to be in MiB.

The minimum size value is typically the size of the finished partition
once _partman_ has done its thing, and the calculated priority determines which
partition gets more space in situations where the requested sizes exceed the
size of the underlying disk. Simple, right? :wink:

## Demo

<http://shady.klausbunny.tv>

## License

GPL
