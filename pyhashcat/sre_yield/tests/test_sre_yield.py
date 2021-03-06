#!/usr/bin/env python2
#
# Copyright 2011-2014 Google Inc.
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

import re
import sys
import unittest

import sre_yield


class YieldTest(unittest.TestCase):
    """Test that regular expressions give the right lists."""

    def testSimpleCases(self):
        self.assertSequenceEqual(sre_yield.AllStrings('1(234?|49?)'),
                                 ['123', '1234', '14', '149'])
        self.assertSequenceEqual(sre_yield.AllStrings('asd|def'),
                                 ['asd', 'def'])
        self.assertSequenceEqual(sre_yield.AllStrings('asd|def\\+|a\\.b\\.c'),
                                 ['asd', 'def+', 'a.b.c'])

    def testOtherCases(self):
        self.assertSequenceEqual(sre_yield.AllStrings('[aeiou]'), list('aeiou'))
        self.assertEqual(len(sre_yield.AllStrings('1.3', flags=re.DOTALL)), 256)
        v = sre_yield.AllStrings('[^-]3[._]1415', flags=re.DOTALL)
        print(list(v))
        self.assertEqual(len(v), 510)
        self.assertEqual(len(sre_yield.AllStrings('(.|5[6-9]|[6-9][0-9])[a-z].?',
                                               flags=re.DOTALL)),
                          300 * 26 * 257)
        self.assertEqual(len(sre_yield.AllStrings('..', charset='0123456789')),
                          100)
        self.assertEqual(len(sre_yield.AllStrings('0*')), 65536)
        # For really big lists, we can't use the len() function any more
        self.assertEqual(sre_yield.AllStrings('0*').__len__(), 65536)
        self.assertEqual(sre_yield.AllStrings('[01]*').__len__(), 2 ** 65536 - 1)

    def testAlternationWithEmptyElement(self):
        self.assertSequenceEqual(sre_yield.AllStrings('a(b|c|)'),
                                 ['ab', 'ac', 'a'])
        self.assertSequenceEqual(sre_yield.AllStrings('a(|b|c)'),
                                 ['a', 'ab', 'ac'])
        self.assertSequenceEqual(sre_yield.AllStrings('a[bc]?'),
                                 ['a', 'ab', 'ac'])
        self.assertSequenceEqual(sre_yield.AllStrings('a[bc]??'),
                                 ['a', 'ab', 'ac'])

    def testSlices(self):
        parsed = sre_yield.AllStrings('[abcdef]')
        self.assertSequenceEqual(parsed[::2], list('ace'))
        self.assertSequenceEqual(parsed[1::2], list('bdf'))
        self.assertSequenceEqual(parsed[1:-1], list('bcde'))
        self.assertSequenceEqual(parsed[1:-2], list('bcd'))
        self.assertSequenceEqual(parsed[1:99], list('bcdef'))
        self.assertSequenceEqual(parsed[1:1], [])

        self.assertEqual(parsed[1], 'b')
        self.assertEqual(parsed[-2], 'e')
        self.assertEqual(parsed[-1], 'f')

    def testSlicesRepeated(self):
        parsed = sre_yield.AllStrings('[abcdef]')
        self.assertSequenceEqual(parsed[::-1][:2], list('fe'))
        self.assertSequenceEqual(parsed[1:][1:][1:-1], list('de'))
        self.assertSequenceEqual(parsed[::2][1:], list('ce'))

    def testGetItemNegative(self):
        parsed = sre_yield.AllStrings('x|[a-z]{1,5}')
        self.assertEqual(parsed[0], 'x')
        self.assertEqual(parsed[1], 'a')
        self.assertEqual(parsed[23], 'w')
        self.assertEqual(parsed[24], 'x')
        self.assertEqual(parsed[25], 'y')
        self.assertEqual(parsed[26], 'z')
        self.assertEqual(parsed[27], 'aa')
        self.assertEqual(parsed[28], 'ab')
        self.assertEqual(parsed[-2], 'zzzzy')
        self.assertEqual(parsed[-1], 'zzzzz')

        # last, and first
        parsed.get_item(len(parsed)-1)
        parsed.get_item(-len(parsed))

        # precisely 1 out of bounds
        self.assertRaises(IndexError, parsed.get_item, len(parsed))
        self.assertRaises(IndexError, parsed.get_item, -len(parsed)-1)

    def testContains(self):
        parsed = sre_yield.AllStrings('[01]+')
        self.assertTrue('0101' in parsed)
        self.assertFalse('0201' in parsed)

    def testNaturalOrder(self):
        parsed = sre_yield.AllStrings('[0-9]{2}')
        self.assertEqual(parsed[0], '00')
        self.assertEqual(parsed[1], '01')
        self.assertEqual(parsed[98], '98')
        self.assertEqual(parsed[99], '99')

    def testCategories(self):
        cat_chars = 'wWdDsS'
        all_ascii = list(map(chr, list(range(256))))
        for c in cat_chars:
            r = re.compile('\\' + c)
            matching = [i for i in all_ascii if r.match(i)]
            self.assertGreater(len(matching), 5)
            parsed = sre_yield.AllStrings('\\' + c)
            self.assertEqual(sorted(matching), sorted(parsed[:]))

    def testDotallFlag(self):
        parsed = sre_yield.AllStrings('.', charset='abc\n')
        self.assertEqual(['a', 'b', 'c'], parsed[:])
        parsed = sre_yield.AllStrings('.', charset='abc\n', flags=re.DOTALL)
        self.assertEqual(['a', 'b', 'c', '\n'], parsed[:])

    def testMaxCount(self):
        parsed = sre_yield.AllStrings('[01]+', max_count=4)
        self.assertEqual('1111', parsed[-1])

    def testParseErrors(self):
        self.assertRaises(sre_yield.ParseError, sre_yield.AllStrings, 'a', re.I)
        self.assertRaises(sre_yield.ParseError, sre_yield.AllStrings, 'a', re.U)
        self.assertRaises(sre_yield.ParseError, sre_yield.AllStrings, 'a', re.L)

    def testSavingGroups(self):
        parsed = sre_yield.AllStrings(r'(([abc])d)e')
        d = {}
        self.assertEqual('ade', parsed.get_item(0, d))
        self.assertEqual('ad', d[1])
        self.assertEqual('a', d[2])

    def testSavingGroupsByName(self):
        parsed = sre_yield.AllMatches(r'x(?P<foo>[abc])x')
        m = parsed[0]
        self.assertEqual('xax', m.group(0))
        self.assertEqual('a', m.group(1))
        self.assertEqual('a', m.group('foo'))

    def testBackrefCounts(self):
        parsed = sre_yield.AllStrings(r'([abc])-\1')
        self.assertEqual(3, len(parsed))
        self.assertEqual(['a-a', 'b-b', 'c-c'], parsed[:])

    def testSlicingMatches(self):
        parsed = sre_yield.AllMatches(r'([abc])-\1')
        self.assertEqual(3, len(parsed))
        self.assertEqual(['a-a', 'b-b'], [x.group(0) for x in parsed[:2]])

    def testAllStringsIsValues(self):
        self.assertEqual(sre_yield.AllStrings, sre_yield.Values)

    def testCanIterateGiantValues(self):
        v = sre_yield.AllStrings('.+')
        self.assertGreater(v.__len__(), sys.maxsize)
        it = iter(v)
        self.assertEqual('\x00', next(it))
        self.assertEqual('\x01', next(it))

    def testCanSliceGiantValues(self):
        v = sre_yield.AllStrings('.+')
        self.assertGreater(v.__len__(), sys.maxsize)
        self.assertEqual(['\x00', '\x01'], list(v[:2]))


if __name__ == '__main__':
    unittest.main()
