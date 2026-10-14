import hashlib
import json
import struct
import unittest
from cast_role_alias import alias_bytes

class AliasTest(unittest.TestCase):
    def fixture(self):
        doc = {'nodes':[{'name':'Mob_Test_Old'},{'name':'root'},{'name':'Mob_Test_Old_Rig'}], 'skins':[{'name':'Mob_Test_Old_Rig','joints':[1]}], 'animations':[{'name':'Walk'}]}
        body=json.dumps(doc).encode();body+=b' '*(-len(body)%4)
        tail=struct.pack('<I4s',4,b'BIN\x00')+b'abcd'
        return struct.pack('<4sII',b'glTF',2,20+len(body)+len(tail))+struct.pack('<I4s',len(body),b'JSON')+body+tail,tail
    def test_alias_preserves_binary_and_unrelated_metadata(self):
        data,tail=self.fixture()
        result,count=alias_bytes(data,'Mob_Test_Old','Mob_Test_New',hashlib.sha256(data).hexdigest())
        self.assertEqual(count,3);self.assertTrue(result.endswith(tail))
        n=struct.unpack_from('<I',result,12)[0];doc=json.loads(result[20:20+n])
        self.assertEqual(doc['nodes'][0]['name'],'Mob_Test_New')
        self.assertEqual(doc['nodes'][1]['name'],'root')
        self.assertEqual(doc['animations'],[{'name':'Walk'}])
        self.assertEqual(doc['skins'][0]['joints'],[1])
    def test_wrong_source_or_absent_name_refused(self):
        data,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'SHA256'):alias_bytes(data,'Mob_Test_Old','Mob_Test_New','0'*64)
        with self.assertRaisesRegex(ValueError,'absent'):alias_bytes(data,'Mob_Test_Missing','Mob_Test_New',hashlib.sha256(data).hexdigest())

if __name__=='__main__':unittest.main(verbosity=2)
