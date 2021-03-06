#!/usr/bin/env python

__author__ = 'pmoreno'

import os
import sys
import unittest
import pkg_resources

sys.path.append( os.path.join(os.path.dirname(__file__), '../../') )

from wft4galaxy.comparators import csv_same_row_and_col_lengths


class TestCSVSameRowAndColLengthsComp(unittest.TestCase):
    def test_run_success(self):
        path_actual = self.__get_resource_path('csv_test_file_actual.csv')
        path_expected = self.__get_resource_path('csv_test_file_expected.csv')
        self.assertTrue(csv_same_row_and_col_lengths(path_actual, path_expected),
                        "Actual and expected file have the same number of rows and cols")

    def test_run_fail_num_cols(self):
        path_actual = self.__get_resource_path('csv_test_file_actual.csv')
        path_expected = self.__get_resource_path('csv_test_file_expected_fail.csv')
        self.assertFalse(csv_same_row_and_col_lengths(path_actual, path_expected),
                         "Actual and expected file have different number of cols")

    def test_run_fail_num_rows(self):
        path_actual = self.__get_resource_path('csv_test_file_actual.csv')
        path_expected = self.__get_resource_path('csv_test_file_expected_fail_2.csv')
        self.assertFalse(csv_same_row_and_col_lengths(path_actual, path_expected),
                         "Actual and expected file have different number of rows")

    @staticmethod
    def __get_resource_path(file_name_in_test_dir):
        resource_path = os.path.join(file_name_in_test_dir)
        return pkg_resources.resource_filename(__name__, resource_path)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestCSVSameRowAndColLengthsComp)


def main():
    result = unittest.TextTestRunner(verbosity=2).run(suite())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
