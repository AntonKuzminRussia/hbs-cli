# -*- coding: utf-8 -*-

import sys
import time
import os
import pytest
import json

sys.path.append('../../')

from libs.common import md5, file_put_contents, file_get_contents
from classes.WorkerThread import WorkerThread
from CommonIntegration import CommonIntegration
from classes.Registry import Registry

class Test_WorkerThread(CommonIntegration):
    thrd = None

    def setup(self):
        if not os.path.exists(Registry().get('config')['main']['path_to_hc']):
            pytest.fail("HC dir not exists")
        self._clean_db()

    def teardown(self):
        if isinstance(self.thrd, WorkerThread):
            del self.thrd
        self._clean_db()

    def test_dict_task(self):
        self._add_hashlist(alg_id=0)
        self._add_hash(hash=md5('123'))
        self._add_hash(hash=md5('456'))
        self._add_hash(hash=md5('ccc'))
        self._add_hash(hash=md5('789'))
        self._add_work_task()

        dicts_path = Registry().get('config')['main']['dicts_path']

        self._add_dict_group()

        self._add_dict()
        self._add_dict(id=2, hash='2')
        file_put_contents(dicts_path + "/1.dict", "aaa\nbbb")
        file_put_contents(dicts_path + "/2.dict", "ccc\nddd")

        self._add_task(source=1)

        self.thrd = WorkerThread(self.db.fetch_row("SELECT * FROM task_works WHERE id = 1"))
        self.thrd.start()

        start_time = int(time.time())
        while True:
            if self.thrd.done:
                break
            if int(time.time()) - start_time > 5:
                pytest.fail("Long time of WorkerThread")
            time.sleep(1)

        wtask = self.db.fetch_row("SELECT * FROM task_works WHERE id = 1")
        assert 'waitoutparse' == wtask['status']
        assert 4 == wtask['uncracked_before']
        assert os.path.exists(wtask['out_file'])
        assert '9df62e693988eb4e1e1444ece0578579:636363\n' == file_get_contents(wtask['out_file'])

    def test_mask_task(self):
        self._add_hashlist(alg_id=0)
        self._add_hash(hash=md5('123'))
        self._add_hash(hash=md5('456'))
        self._add_hash(hash=md5('ccc'))
        self._add_hash(hash=md5('789'))
        self._add_work_task()
        self._add_task(source='?l?l?l', type='mask')

        self.thrd = WorkerThread(self.db.fetch_row("SELECT * FROM task_works WHERE id = 1"))
        self.thrd.start()

        start_time = int(time.time())
        while True:
            if self.thrd.done:
                break
            if int(time.time()) - start_time > 5:
                pytest.fail("Long time of WorkerThread")
            time.sleep(1)

        wtask = self.db.fetch_row("SELECT * FROM task_works WHERE id = 1")
        assert 'waitoutparse' == wtask['status']
        assert 4 == wtask['uncracked_before']
        assert os.path.exists(wtask['out_file'])
        assert '9df62e693988eb4e1e1444ece0578579:636363\n' == file_get_contents(wtask['out_file'])

    def test_dictmask_task(self):
        self._add_hashlist(alg_id=0)
        self._add_hash(hash=md5('123'))
        self._add_hash(hash=md5('456'))
        self._add_hash(hash=md5('ccc1'))
        self._add_hash(hash=md5('789'))
        self._add_work_task()
        self._add_task(source=json.dumps({'mask': '?d', 'dict': 1}), type='dictmask')

        dicts_path = Registry().get('config')['main']['dicts_path']

        self._add_dict_group()

        self._add_dict()
        self._add_dict(id=2, hash='2')
        file_put_contents(dicts_path + "/1.dict", "aaa\nbbb\n")
        file_put_contents(dicts_path + "/2.dict", "ccc\nddd\n")

        self.thrd = WorkerThread(self.db.fetch_row("SELECT * FROM task_works WHERE id = 1"))
        self.thrd.start()

        start_time = int(time.time())
        while True:
            if self.thrd.done:
                break
            if int(time.time()) - start_time > 5:
                pytest.fail("Long time of WorkerThread")
            time.sleep(1)

        wtask = self.db.fetch_row("SELECT * FROM task_works WHERE id = 1")
        assert 'waitoutparse' == wtask['status']
        assert 4 == wtask['uncracked_before']
        assert os.path.exists(wtask['out_file'])
        assert 'a026017b65ddb74ee6e2591171285146:63636331\n' == file_get_contents(wtask['out_file'])

    def test_maskdict_task(self):
        self._add_hashlist(alg_id=0)
        self._add_hash(hash=md5('123'))
        self._add_hash(hash=md5('456'))
        self._add_hash(hash=md5('1ccc'))
        self._add_hash(hash=md5('789'))
        self._add_work_task()
        self._add_task(source=json.dumps({'mask': '?d', 'dict': 1}), type='maskdict')

        dicts_path = Registry().get('config')['main']['dicts_path']

        self._add_dict_group()

        self._add_dict()
        self._add_dict(id=2, hash='2')
        file_put_contents(dicts_path + "/1.dict", "aaa\nbbb\n")
        file_put_contents(dicts_path + "/2.dict", "ccc\nddd\n")

        self.thrd = WorkerThread(self.db.fetch_row("SELECT * FROM task_works WHERE id = 1"))
        self.thrd.start()

        start_time = int(time.time())
        while True:
            if self.thrd.done:
                break
            if int(time.time()) - start_time > 5:
                pytest.fail("Long time of WorkerThread")
            time.sleep(1)

        wtask = self.db.fetch_row("SELECT * FROM task_works WHERE id = 1")
        assert 'waitoutparse' == wtask['status']
        assert 4 == wtask['uncracked_before']
        assert os.path.exists(wtask['out_file'])
        assert '49a14108270c0596ac1d70c3c4f82a10:31636363\n' == file_get_contents(wtask['out_file'])