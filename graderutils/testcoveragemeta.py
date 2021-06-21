"""
Can be used to generate coverage-tests for user uploaded tests

To create a new coverage-test create a ``coverage_tests.py`` with necessary imports and class TestCoverage with TestCoverageMeta as it's metaclass. Example:

```python
class TestCoverage(unittest.TestCase, metaclass=TestCoverageMeta, testmodule="usertest", filename="userfile", points=[8, 10, 12]):
    pass
```
The keyword arguments are:

Argument  | Function
--------  | --------
testmodule| the name of the test module user uploaded
filename  | the name of the file that you check the coverage for
points    | list of points for different coverage amounts

This example would run usertest (from test import Test as usertest) and check coverages for userfile.py.
It would give 8 points if 33.33% of userfile.py would be covered, 10 points more if 66.66% and 12 points if 100%
totaling 30 points.
If you give a list with 5 point amounts it would check coverage in 20% intervals.
It will give 0 points out of the total if all of the users tests won't succeed

Because you don't want grader to run users tests as graded tests (because crafty users could add (1000p) to their tests and it shows up ugly) you should also add

```python
def load_tests(*args, **kwargs):
    return unittest.TestLoader().loadTestFromTestCase(TestCoverage)
```
in ``coverage_tests.py``
"""
import importlib
import sys
import unittest
from io import StringIO

import coverage

from graderutils import graderunittest


class TestCoverageMeta(type):
    """
    Used to automatically create coverage-tests for student tests

    Keyword arguments:
    test     -- the test class student uploaded
    filename -- the name of the file that you check the coverage for
    points   -- list of points for different coverage amounts
    minimum    -- The percentage from which the points are started


    To create a new coverage-test create coverage_tests.py with necessary imports and
    class TestCoverage(unittest.TestCase, metaclass=TestCoverageMeta, testmodule="test", filename="userfile.py", points=[8, 10, 12]):
        pass

    This example would import test, run it and check coverages for userfile.py.
    It would give 8 points if 33.33% of userfile.py would be covered, 10 points more if 66.66% and 12 points if 100%
    totaling 30 points.
    If you give a list of 5 points it would check coverage in 20% intervals.
    It will give 0 points out of the total if all of the users tests won't succeed

    Because you don't want grader to run users tests as grader_test (giving themselves points)
    you should also
    def load_tests(*args, **kwargs):
        return unittest.TestLoader().loadTestFromTestCase(TestCoverage)
    in coverage_tests.py
    """
    def __new__(cls, clsname, bases, dct, testmodule, filename, points, minimum=0):
        newclass = super(TestCoverageMeta, cls).__new__(cls, clsname, bases, dct)
        stream = StringIO()
        cov = coverage.Coverage()
        cov.start()
        # we need to import the files here and make sure that
        # the users file is reloaded so that coverage shows right
        # lines as covered. It would miss function definitions otherwise
        test = importlib.import_module(testmodule)
        mod = importlib.import_module(filename)
        importlib.reload(mod)
        suite = unittest.TestLoader().loadTestsFromModule(test)
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        cov.stop()
        covered = cov.report(include="{}.py".format(filename), show_missing=True, file=sys.stderr)
        missing = cov.analysis("{}.py".format(filename))[3]

        @graderunittest.points(0)
        def user_tests_pass(self):
            """Check if students tests pass"""
            if not result.wasSuccessful():
                self.fail("Your tests didn't pass. Coverage tests won't be run.\n\n{}".format(stream.getvalue()))
            self.preformatted_feedback = "Run results: \n{}".format(stream.getvalue())

        setattr(newclass, 'test_code', user_tests_pass)

        def generate_test(percentage, test_num, points):
            @graderunittest.points(points)
            def a_test(self):
                if result.wasSuccessful():
                    self.assertGreaterEqual(covered, percentage,
                        "\nYour code covers only {:.2f}%\nMissing lines: {}"
                        .format(covered, missing))
                else:
                    self.fail("Test wasn't run because your tests weren't successful")

            a_test.__doc__ = 'Checks that test coverage is over {}%'.format(percentage)
            setattr(newclass, 'test_coverage_{:02d}'.format(test_num), a_test)

        iterations = len(points)
        for num, point in enumerate(points, start=1):
            generate_test((100-minimum)/iterations*num+minimum, num, point)

        return newclass


    def __init__(cls, clsname, bases, dct, testmodule, filename, points, minimum=0):
        super().__init__(cls, clsname, dct)
