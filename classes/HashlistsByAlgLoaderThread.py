# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Thread for compile hashlists by common (one) alg
"""

import time

from classes.Registry import Registry
from classes.Factory import Factory
from classes.CommonThread import CommonThread
from libs.common import gen_random_md5


class HashlistsByAlgLoaderThread(CommonThread):
    """ Thread for compile hashlists by common (one) alg """
    current_hashlist_id = None
    DELIMITER = 'UNIQUEDELIMITER'
    delay_per_check = None
    thread_name = "hashlist_common_loader"

    def __init__(self):
        """ Initialization """
        CommonThread.__init__(self)

        self.delay_per_check = int(self.config['main']['hashlists_by_alg_loader_delay_per_try'])

    def get_common_hashlist_id_by_alg(self, alg_id):
        """
        Return id of common hashlist by alg
        :param alg_id:
        :return int:
        """
        hashlist_id = self._db.fetch_one("SELECT id FROM hashlists WHERE common_by_alg = {0}".format(alg_id))
        if hashlist_id is None:
            alg_name = self._db.fetch_one("SELECT name FROM algs WHERE id = {0}".format(alg_id))
            hashlist_id = self._db.insert(
                "hashlists",
                {
                    'name': 'All-{0}'.format(alg_name),
                    'alg_id': alg_id,
                    'have_salts': int(self.is_alg_have_salts(alg_id)),
                    'delimiter': self.DELIMITER,
                    'parsed': '0',
                    'tmp_path': '',
                    'status': 'ready',
                    'when_loaded': int(time.time()),
                    'common_by_alg': alg_id,
                }
            )
        return hashlist_id

    def get_current_work_hashlist(self):
        """
        Get hashlist id which now in work
        :return int:
        """
        return self._db.fetch_one("SELECT hashlist_id FROM task_works WHERE status='work'")

    def get_hashlist_status(self, hashlist_id):
        """
        Return hashlist status
        :param hashlist_id:
        :return str:
        """
        return self._db.fetch_one("SELECT status FROM hashlists WHERE id = {0}".format(hashlist_id))

    def is_alg_in_parse(self, alg_id):
        """
        Is this alg now in parse?
        :param alg_id:
        :return:
        """
        result = self._db.fetch_one(
            "SELECT t.id FROM `task_works` t, `hashlists` hl "
            "WHERE t.hashlist_id = hl.id AND hl.alg_id = {0} "
            "AND t.status IN('waitoutparse','outparsing')".format(alg_id)
        )
        return bool(result)

    def hashes_count_in_hashlist(self, hashlist_id):
        """ Count all hashes of hashlist """
        return self._db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hashlist_id = {0}".format(hashlist_id))

    def hashes_count_by_algs(self):
        """ return named dict with algs ids and uncracked hashes count """
        return self._db.fetch_pairs(
            "SELECT hl.alg_id, COUNT(DISTINCT h.summ) FROM `hashes` h, hashlists hl "
            "WHERE h.hashlist_id = hl.id AND h.cracked = 0 AND hl.common_by_alg = 0 "
            "GROUP BY hl.alg_id"
        )

    def is_alg_have_salts(self, alg_id):
        """
        Is this alg has salts?
        :param alg_id:
        :return:
        """
        return bool(
            self._db.fetch_one(
                "SELECT have_salts FROM hashlists WHERE alg_id = {0} ORDER BY have_salts DESC LIMIT 1".format(alg_id)
            )
        )

    def get_possible_hashlist_and_alg(self):
        """ Get possible hashlist and alg for build/update """
        hashes_by_algs_count = self.hashes_count_by_algs()
        for alg_id in hashes_by_algs_count:
            hashlist_id = self.get_common_hashlist_id_by_alg(alg_id)

            hashes_count_in_hashlist = self.hashes_count_in_hashlist(hashlist_id)
            if hashes_count_in_hashlist == hashes_by_algs_count[alg_id]:
                continue

            if self.is_alg_in_parse(alg_id):
                self.log(
                    "Skip alg, it parsing or wait parse #{0}".format(
                        alg_id
                    )
                )
                continue

            if hashlist_id == self.get_current_work_hashlist() or \
                            self.get_hashlist_status(hashlist_id) != 'ready':
                self.log(
                    "Skip it, it in work or not ready #{0}/{1}/{2}".format(
                        hashlist_id,
                        self.get_current_work_hashlist(),
                        self.get_hashlist_status(hashlist_id)
                    )
                )
                continue

            self.log(
                "Build list for alg #{0} ({1} vs {2})".format(
                    alg_id,
                    hashes_count_in_hashlist,
                    hashes_by_algs_count[alg_id]
                )
            )
            return {'hashlist_id' : hashlist_id, 'alg_id' : alg_id}
        return None

    def clean_old_hashes(self, hashlist_id):
        """
        Clean all hashes of hashlist
        :param hashlist_id:
        :return:
        """
        self._db.q("DELETE FROM hashes WHERE hashlist_id = {0}".format(hashlist_id))
        self._db.q("UPDATE hashlists SET cracked=0, uncracked=0 WHERE id = {0}".format(hashlist_id))

    def put_all_hashes_of_alg_in_file(self, alg_id):
        """
        Place all hashes of alg in txt file
        :param alg_id:
        :return:
        """
        curs = self._db.q(
            "SELECT CONCAT(h.hash, '{0}', h.salt) as hash FROM hashes h, hashlists hl "
            "WHERE hl.id = h.hashlist_id AND hl.alg_id = {1} AND hl.common_by_alg = 0 AND h.cracked = 0".format(
                self.DELIMITER, alg_id)
            if self.is_alg_have_salts(alg_id) else
            "SELECT h.hash FROM hashes h, hashlists hl "
            "WHERE hl.id = h.hashlist_id AND hl.alg_id = {0} AND hl.common_by_alg = 0 AND h.cracked = 0".format(alg_id),
            True
        )

        tmp_path = self.tmp_dir + "/" + gen_random_md5()
        fh = open(tmp_path, 'w')
        for row in curs:
            _hash = row[0].strip()
            if not len(_hash) or _hash == self.DELIMITER:
                continue
            fh.write("{0}\n".format(_hash))
        fh.close()

        return tmp_path

    def run(self):
        """ Run thread """
        try:
            while self.available:
                candidate = self.get_possible_hashlist_and_alg()
                if candidate is not None:
                    hashlist_id = candidate['hashlist_id']
                    alg_id = candidate['alg_id']

                    # Mark as 'parsing' for HashlistsLoader don`t get it to work before we done
                    self._db.update("hashlists", {'parsed': 0, 'status': 'parsing'}, "id = {0}".format(hashlist_id))

                    self.log("Delete old hashes of #{0}".format(hashlist_id))
                    self.clean_old_hashes(hashlist_id)

                    self.log("Put data in file for #{0}".format(hashlist_id))
                    tmp_path = self.put_all_hashes_of_alg_in_file(alg_id)

                    self._db.update("hashlists",
                                    {'status': 'wait', 'tmp_path': tmp_path, "when_loaded": int(time.time())},
                                    "id = {0}".format(hashlist_id))

                    self.log("Done #{0}".format(hashlist_id))

                time.sleep(self.delay_per_check)
        except BaseException as ex:
            self.exception(ex)
