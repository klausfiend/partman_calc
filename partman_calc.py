#!/usr/bin/env python

import cherrypy
import pygal
import random
import re
import string
from pygal.style import CleanStyle

default_partitions = ('/boot', '/', '/var', '/tmp', '/home', 'swap')
default_formats = {"stacked": "Stacked Bar Graph", "pie": "Pie Graph", "partman": "Partman Recipe"}


class PartmanCalculator(object):
    @cherrypy.expose
    def index(self):
        form_head = """<html>
<head>
<title>Partman Calculator and Visualizer</title>
<style type="text/css">
html * {
    font-size: 1em !important;
    color: #000 !important;
    font-family: Arial !important;
}
</style>
</head>
<body>
    <form method="post" action="calculate">
        <table>
        <tr>
            <th>Name</th>
            <th>Min Size</th>
            <th>Priority</th>
            <th>Max Size</th>
        </tr>"""
        form_body = ''
        for i in range(len(default_partitions)):
            form_body += '\t\t<tr>\n \
\t\t\t<td><input type="text" length="9" name="input{}" value="{}" /></td>\n \
\t\t\t<td><input type="text" length="5" name="min_size{}" value="0" /></td>\n \
\t\t\t<td><input type="text" length="5" name="priority{}" value="0" /></td>\n \
\t\t\t<td><input type="text" length="5" name="max_size{}" value="0" /></td>\n \
\t\t</tr>\n'.format(i, default_partitions[i], i, i, i)

        form_body += '\t\t<tr><td>Free Disk Space</td><td><input type="text" length="9" name="disk_size" /></td><td>MiB</td></tr>\n'
        form_body += '\t\t<tr><td>RAM Available</td><td><input type="text" length="9" name="ram_avail" /></td><td>MiB</td></tr>\n'
        form_body += '\t\t<tr><td>Graph Style</td>\n\t\t\t<td>\n\t\t\t\t<select name="graph">\n'
        for k, v in default_formats.iteritems():
            if k == 'stacked':
                form_body += '\t\t\t\t<option value="{}" selected>{}</option>\n'.format(k, v)
            else:
                form_body += '\t\t\t\t<option value="{}">{}</option>\n'.format(k, v)
        form_body += '\t\t\t\t</select>\n\t\t\t</td>\n\t\t</tr>'

        form_foot = """
        <tr><td></td><td><button type="submit">Show me!</button></td></tr>
        </table>
    </form>
</body>
</html>"""
        return form_head + form_body + form_foot

    @cherrypy.expose
    def calculate(self, **kwargs):
        display_format = kwargs['graph']
        try:
            ram_avail = int(kwargs['ram_avail'])
        except:
            cherrypy.response.status = '405'
            return "Missing or invalid RAM size ... d'oh"
        try:
            disk_size = int(kwargs['disk_size'])
        except:
            cherrypy.response.status = '405'
            return "Missing or invalid disk size ... d'oh"

        # skip any interpretation of the inputs and just return a recipe mapped from the inputs
        if display_format == 'partman':
            cherrypy.response.headers['Content-Type']= 'text/plain'
            return partman_recipe(kwargs)

        # split the partition information into a list of lists that maps back
        # to values in **kwargs
        kv_pairs = [["input{}".format(i), "min_size{}".format(i), "priority{}".format(i), "max_size{}".format(i)] for i in range(len(default_partitions))]

        # convert **kwargs into a list to preserve partition ordering, and
        # within each list element, create a list containing the partition name
        # as the first element and a list containing the partition attributes
        # as the second element; there are four entries in each kv_pairs[i]
        # entry, hence the arguments to range()
        #
        # the result should resemble something like this:
        #
        #   inputs = [
        #       [u'/boot', [128, 132, 128]],
        #       [u'/', [8192, 8196, 17176]],
        #       [u'/var', [16384, 16386, 16384]],
        #       [u'swap', [8192, 8192, 8588]]
        #   ]
        #
        # This ensures that output order matches input order.
        #
        inputs = []
        try:
            for i in range(len(kv_pairs)):
                # discard any inputs that have empty fields
                if '' not in [kwargs[kv_pairs[i][x]] for x in range(0, 4)]:
                    # convert any number-like strings into real numbers
                    inputs.append(list([kwargs[kv_pairs[i][0]], map(lambda x: numberify(x, ram_avail), [kwargs[kv_pairs[i][x]] for x in range(1, 4)])]))
        except:
            cherrypy.response.status = '405'
            return "Invalid partition information somewhere ... d'oh ... maybe a missing or invalid field?"

        partman_results = partman_algorithm(disk_size, ram_avail, inputs)
        data_points = [[partman_results[i][0], partman_results[i][1][0]] for i in range(len(partman_results))]
        try:
            cherrypy.response.headers['Content-Type']= 'image/svg+xml'
            return graph_results(display_format, disk_size, data_points)
        except:
            cherrypy.response.status = '405'
            return "Something went wrong ... d'oh"


# this algorithm is adopted from the method found here:
#   https://anonscm.debian.org/cgit/d-i/partman-auto.git/tree/lib/recipes.sh
# specifically, the 'expand_scheme' function. Documentation of the underlying
# algorithm can be found here:
#   https://anonscm.debian.org/cgit/d-i/debian-installer.git/tree/doc/devel/partman-auto-recipe.txt
def partman_algorithm(disk_size, ram_avail, inputs):
    free_space = int(disk_size)
    N = len(inputs)

    labels = [inputs[i][0] for i in range(N)]
    minimum = [inputs[i][1][0] for i in range(N)]
    factors = [inputs[i][1][1] for i in range(N)]
    maximum = [inputs[i][1][2] for i in range(N)]

    for i in range(N):
        if maximum[i] != -1 and maximum[i] < minimum[i]:
            maximum[i] = minimum[i]
        if factors[i] < minimum[i]:
            factors[i] = minimum[i]

    minsum = sum(minimum)
    factsum = sum(factors) - minsum
    if factsum == 0:
        factsum = 100

    prev_minimum = prev_factors = prev_maximum = []
    factors = [(factors[i] - minimum[i]) * 100 / factsum for i in range(N)]
    ready = False
    while not ready:
        if prev_minimum != minimum or prev_factors != factors or prev_maximum != maximum:
            prev_minimum = list(minimum)
            prev_factors = list(factors)
            prev_maximum = list(maximum)
        else:
            ready = True

        factsum = sum(factors)
        minsum = sum(minimum)
        unallocated = 0 if ((free_space - minsum) < 0) else free_space - minsum

        for i in range(N):
            if factsum == 0:
                x = minimum[i]
                if factors[i] < 0:
                    factors[i] = 0
            else:
                x = minimum[i] + unallocated * factors[i] / factsum

            if maximum[i] != -1 and x > maximum[i]:
                minimum[i] = maximum[i]
                factors[i] = 0
            elif x < minimum[i]:
                maximum[i] = minimum[i]
                factors[i] = 0
            else:
                minimum[i] = x

    outputs = []
    for i in range(N):
        outputs.append([labels[i], [minimum[i], factors[i], maximum[i]]])
    return outputs


# generate an SVG with PyGal
def graph_results(display_format, disk_size, data_points):
    disk_in_human = bytes_to_human(disk_size)
    allocated_space = sum([data_points[i][1] for i in range(len(data_points))])
    empty_space = disk_size - allocated_space
    if empty_space != 0:
        data_points.append(['unallocated', empty_space])

    if display_format == 'pie':
        chart = pygal.Pie(inner_radius=.3333333333, height=800)
        chart.config(style=CleanStyle)
    else:
        chart = pygal.HorizontalStackedBar(height=250, x_title='Size in MB')
        
    for i in range(len(data_points)):
        chart.add(data_points[i][0], [{
            'label': "{} ({}%)".format(bytes_to_human(data_points[i][1]), make_percent(data_points[i][1], disk_size)),
            'value': data_points[i][1]}])

    chart.human_readable = True
    chart.print_values = False
    chart.title = "Theoretical Partition Sizing for {} Disk".format(disk_in_human)
    return chart.render()


# generate a text blob that can be used as a partman recipe
def partman_recipe(kwargs):
    # generate a list of the defined partitions
    inputs = []
    for i in range(len(default_partitions)):
        params = ['input{}'.format(i), 'min_size{}'.format(i), 'priority{}'.format(i), 'max_size{}'.format(i)]
        kv_list = []
        for p in params:
            kv_list.append(kwargs[p])
        inputs.append(kv_list)

    # generate a label for the partition recipe
    labels = []
    for i in range(len(default_partitions)):
        p = 'input{}'.format(i)
        if kwargs[p] == "/":
            labels.append("root")
        elif kwargs[p] == "swap" or kwargs[p] == '':
            pass
        else:
            p = kwargs[p].replace("/", "")
            labels.append(p)
    result = "-".join(labels) + " ::\n"

    # generate partition directives for the recipe
    for i in range(len(default_partitions)):
        p = 'input{}'.format(i)
        if kwargs[p] != '' and all(inputs[i]):
            if kwargs[p].find("boot") != -1:
                result += "{} {} {} ext3 $primary{{ }} $bootable{{ }} method{{ format }} format{{ }} use_filesystem{{ }} filesystem{{ ext4 }} mountpoint{{ {} }} .\n".format(inputs[i][1], inputs[i][2], inputs[i][3], inputs[i][0])
            elif kwargs[p].find("swap") != -1:
                result += "{} {} {} linux-swap method{{ swap }} format{{ }} .\n".format(inputs[i][1], inputs[i][2], inputs[i][3])
            else:
                result += "{} {} {} ext3 method{{ format }} format{{ }} use_filesystem{{ }} filesystem{{ ext4 }} mountpoint{{ {} }} .\n".format(inputs[i][1], inputs[i][2], inputs[i][3], inputs[i][0])
    return result


# convert size+percent, percent, and/or size strings to valid numbers
def numberify(x, ram_size):
    size_percent_re = re.compile('[0-9][0-9]*\+[0-9][0-9]*%$')
    percent_re = re.compile('[0-9][0-9]*%$')
    if size_percent_re.match(x):
        size = int(x.split('+')[0])
        percent = int(x.split('+')[1].split('%')[0])
        result = size + ram_size * percent / 100
    elif percent_re.match(x):
        percent = int(x.split('%')[0])
        result = ram_size * percent / 100
    else:
        try:
            result = int(x)
        except ValueError:
            raise
    return result
    

# convert a value to a percent
def make_percent(numerator, denominator):
    return float("{0:.2f}".format((float(numerator) / float(denominator) * 100)))


# convert a disk size in MB to the nearest convenient human-readable unit
def bytes_to_human(nMbytes):
    suffixes = ['MiB', 'GiB', 'TiB', 'PiB']
    if nMbytes == 0: return '0 B'
    i = 0
    while nMbytes >= 1000 and i < len(suffixes) - 1:
        nMbytes /= 1000.
        i += 1
    f = ('%.2f' % nMbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


if __name__ == '__main__':
    ### unit tests
    test_input = []
    test_input.append([[u'boot', [100, 300, 200]], [u'/', [4000, 10000, 10000]], [u'/tmp', [500, 9000, 2000]], [u'/var', [6000, 9000, 20000]], ['swap', [512, 512, '200%']], [u'home', [40000, 60000, 100000000]]])
    test_input.append([[u'boot', [100, 300, 200]], [u'root', [4000, 10000, 10000]], [u'tmp', [500, 9000, 2000]], [u'var', [6000, 9000, 20000]], [u'swap', [512, 512, '200%']], [u'home', [40000, 60000, -1]]])
    test_input.append([[u'var', [16384, 16386, 16384]], [u'root', [8192, 8196, '400%']], [u'boot', [128, 132, 128]], [u'swap', [8192, 8192, '200%']]])
    test_input.append([[u'var', [16384, 16386, 16384]], [u'root', [8192, 8196, '400%']], [u'boot', [128, 132, 128]], [u'swap', ['100%', 8192, '200%']]])
    for inputs in test_input:
        for i in range(len(inputs)):
            for x in range(len(inputs[i][1])):
                if str(inputs[i][1][x]).find('%') != -1:
                    inputs[i][1][x] = numberify(inputs[i][1][x], 4294)
	print("inputs: " + str(inputs))
        outputs = partman_algorithm(250000, 4294, inputs)
	print("outputs: " + str(outputs) + "\n")

    cherrypy.config.update({
            "server.socket_host": '0.0.0.0',
            "server.socket_port": 8080,
                })
    cherrypy.quickstart(PartmanCalculator())
else:
    application = cherrypy.Application(PartmanCalculator())
