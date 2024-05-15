#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""LenMa: Length Matters Syslog Message Clustering.
"""

import json

import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.metrics.pairwise import cosine_similarity

__all__ = ['LenmaTemplateManager']


class _Template(object):
    def __init__(self, index, words, logid):
        self._index = index
        self._words = words
        self._nwords = len(words)
        self._counts = 1
        self._logid = [logid]

    @property
    def index(self):
        return self._index

    @property
    def words(self):
        return self._words

    @property
    def nwords(self):
        return self._nwords

    @property
    def counts(self):
        return self._counts

    def _dump_as_json(self):
        """Dumps the data structure as a JSON format to serialize the
        object.

        This internal function is called by the TemplateManager
        class.
        """
        assert (False)

    def _restore_from_json(self, data):
        """Initializes the instance with the provided JSON data.

        This internal function is normally called by the initializer.
        """
        assert (False)

    def get_similarity_score(self, new_words):
        """Retruens a similarity score.

        Args:
          new_words: An array of words.

        Returns:
          score: in float.
        """
        assert (False)

    def update(self, new_words):
        """Updates the template data using the supplied new_words.
        """
        assert (False)

    def __str__(self):
        template = ' '.join([self.words[idx] if self.words[idx] != '' else '*' for idx in range(self.nwords)])
        return '{index}({nwords})({counts}):{template}'.format(
            index=self.index,
            nwords=self.nwords,
            counts=self._counts,
            template=' '.join([self.words[idx] if self.words[idx] != '' else '*' for idx in range(self.nwords)]))


class _LenmaTemplate(_Template):
    def __init__(self, index=None, words=None, logid=None, json=None):
        if json is not None:
            # restore from the jsonized data.
            self._restore_from_json(json)
        else:
            # initialize with the specified index and words vlaues.
            assert (index is not None)
            assert (words is not None)
            self._index = index
            self._words = words
            self._nwords = len(words)
            self._wordlens = [len(w) for w in words]
            self._counts = 1
            self._logid = [logid]

    @property
    def wordlens(self):
        return self._wordlens

    def _dump_as_json(self):
        description = str(self)
        return json.dumps([self.index, self.words, self.nwords, self.wordlens, self.counts])

    def _restore_from_json(self, data):
        (self._index,
         self._words,
         self._nwords,
         self._wordlens,
         self._counts) = json.loads(data)

    def _try_update(self, new_words):
        try_update = [self.words[idx] if self._words[idx] == new_words[idx]
                      else '' for idx in range(self.nwords)]
        if (self.nwords - try_update.count('')) < 3:
            return False
        return True

    def _get_accuracy_score(self, new_words):
        # accuracy score
        # wildcard word matches any words
        fill_wildcard = [self.words[idx] if self.words[idx] != ''
                         else new_words[idx] for idx in range(self.nwords)]
        ac_score = accuracy_score(fill_wildcard, new_words)
        return ac_score

    def _get_wcr(self):
        return self.words.count('') / self.nwords

    def _get_accuracy_score2(self, new_words):
        # accuracy score 2
        # wildcard word matches nothing
        wildcard_ratio = self._get_wcr()
        ac_score = accuracy_score(self.words, new_words)
        return (ac_score / (1 - wildcard_ratio), wildcard_ratio)

    def _get_similarity_score_cosine(self, new_words):
        # cosine similarity
        wordlens = np.asarray(self._wordlens).reshape(1, -1)
        new_wordlens = np.asarray([len(w) for w in new_words]).reshape(1, -1)
        cos_score = cosine_similarity(wordlens, new_wordlens)
        return cos_score

    def _get_similarity_score_jaccard(self, new_words):
        ws = set(self.words) - set('')
        nws = set([new_words[idx] if self.words[idx] != '' else ''
                   for idx in range(len(new_words))]) - set('')
        return len(ws & nws) / len(ws | nws)

    def _count_same_word_positions(self, new_words):
        c = 0
        for idx in range(self.nwords):
            if self.words[idx] == new_words[idx]:
                c = c + 1
        return c

    def get_similarity_score(self, new_words):
        # heuristic judge: the first word (process name) must be equal
        if self._words[0] != new_words[0]:
            return 0

        # check exact match
        ac_score = self._get_accuracy_score(new_words)
        if ac_score == 1:
            return 1

        cos_score = self._get_similarity_score_cosine(new_words)

        case = 6
        if case == 1:
            (ac2_score, ac2_wcr) = self._get_accuracy_score2(new_words)
            if ac2_score < 0.5:
                return 0
            return cos_score
        elif case == 2:
            (ac2_score, ac2_wcr) = self._get_accuracy_score2(new_words)
            return (ac2_score + cos_score) / 2
        elif case == 3:
            (ac2_score, ac2_wcr) = self._get_accuracy_score2(new_words)
            return ac2_score * cos_score
        elif case == 4:
            (ac2_score, ac2_wcr) = self._get_accuracy_score2(new_words)
            print(ac2_score, ac2_wcr)
            tw = 0.5
            if ac2_score < tw + (ac2_wcr * (1 - tw)):
                return 0
            return cos_score
        elif case == 5:
            jc_score = self._get_similarity_score_jaccard(new_words)
            if jc_score < 0.5:
                return 0
            return cos_score
        elif case == 6:
            if self._count_same_word_positions(new_words) < 3:
                return 0
            return cos_score

    def update(self, new_words, logid):
        self._counts += 1
        self._wordlens = [len(w) for w in new_words]
        # self._wordlens = [(self._wordlens[idx] + len(new_words[idx])) / 2
        #                  for idx in range(self.nwords)]
        self._words = [self.words[idx] if self._words[idx] == new_words[idx]
                       else '' for idx in range(self.nwords)]
        self._logid.append(logid)

    def print_wordlens(self):
        print('{index}({nwords})({counts}):{vectors}'.format(
            index=self.index,
            nwords=self.nwords,
            counts=self._counts,
            vectors=self._wordlens))

    def get_logids(self):
        return self._logid


class _TemplateManager(object):
    def __init__(self):
        self._templates = []

    @property
    def templates(self):
        return self._templates

    def infer_template(self, words):
        """Infer the best matching template, or create a new template if there
        is no similar template exists.

        Args:
          words: An array of words.

        Returns:
          A template instance.

        """
        assert (False)

    def dump_template(self, index):
        """Dumps a specified template data structure usually in a text
        format.

        Args:
          index: a template index.

        Returns:
          A serialized text data of the specified template.
        """
        assert (False)

    def restore_template(self, data):
        """Creates a template instance from data (usually a serialized
        data when LogDatabase.close() method is called.

        This function is called by the LogDatabase class.

        Args:
          data: a data required to rebuild a template instance.

        Returns:
          A template instance.
        """
        assert (False)

    def _append_template(self, template):
        """Append a template.

        This internal function may be called by the LogDatabase
        class too.

        Args:
          template: a new template to be appended.

        Returns:
          template: the appended template.
        """
        assert (template.index == len(self.templates))
        self.templates.append(template)
        return template


class LenmaTemplateManager(_TemplateManager):
    def __init__(self,
                 threshold=0.9,
                 predefined_templates=None):
        self._templates = []
        self._threshold = threshold
        if predefined_templates:
            for template in predefined_templates:
                self._append_template(template)

    def dump_template(self, index):
        return self.templates[index]._dump_as_json()

    def restore_template(self, data):
        return _LenmaTemplate(json=data)

    def infer_template(self, words, logid):
        nwords = len(words)

        candidates = []
        for (index, template) in enumerate(self.templates):
            if nwords != template.nwords:
                continue
            score = template.get_similarity_score(words)
            if score < self._threshold:
                continue
            candidates.append((index, score))
        candidates.sort(key=lambda c: c[1], reverse=True)

        if len(candidates) > 0:
            index = candidates[0][0]
            self.templates[index].update(words, logid)
            return self.templates[index]

        new_template = self._append_template(
            _LenmaTemplate(len(self.templates), words, logid))
        return new_template

