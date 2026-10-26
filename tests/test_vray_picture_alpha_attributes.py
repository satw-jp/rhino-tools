"""Regression: ObjectAttributes and TextureMapping expose ToJSON, not DataCRC."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

spec = importlib.util.spec_from_file_location(
    'alpha_attributes', Path(__file__).resolve().parents[1] / 'scripts/rhino8_vray_picture_alpha.py')
alpha = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alpha)


class SerializedOnly:
    def __init__(self, payload):
        self.payload = payload

    def ToJSON(self, options):
        return json.dumps(self.payload)

    def Duplicate(self):
        return SerializedOnly(copy.deepcopy(self.payload))


class Matrix:
    def __init__(self, offset=0):
        self.offset = offset

    def __getitem__(self, key):
        row, col = key
        return self.offset if (row, col) == (0, 3) else int(row == col)


class AttributeRegressionTests(unittest.TestCase):
    def host(self):
        host = alpha.RhinoHost.__new__(alpha.RhinoHost)
        host.serialization = object()
        host.generation = 0
        host.R = NS(Render=NS(
            ContentUuids=NS(PictureMaterialType='picture', BitmapTextureType='bitmap',
                            SimpleBitmapTextureType='simple'),
            RenderMaterial=NS(StandardChildSlots=NS(Diffuse=0))),
            Geometry=NS(Transform=NS(Identity=Matrix())))
        simulation = NS(LocalMappingTransform=Matrix(), MappingChannel=1,
                        ProjectionMode='MappingChannel', Repeating=True, Dispose=lambda: None)
        bitmap = NS(TypeId='bitmap', RenderHash=123, Filename='image.png',
                    SimulatedTexture=lambda generation: simulation)
        material = NS(TypeId='picture', GetTextureFromUsage=lambda usage: bitmap)
        obj = NS(Id='one', IsPictureFrame=True, IsLocked=False, IsReference=False,
                 IsInstanceDefinitionGeometry=False, HasSubobjectMaterials=False,
                 HasDynamicTransform=False, GetRenderMaterial=lambda front: material,
                 Attributes=SerializedOnly({'layer': 1, 'userdata': {'original': True}}),
                 Geometry=NS(DataCRC=lambda seed: 99), GetTextureChannels=lambda: [])
        def modify(object_id, attributes, quiet):
            obj.Attributes = attributes.Duplicate()
            return True
        host.doc = NS(Objects=NS(FindId=lambda object_id: obj, ModifyAttributes=modify))
        return host, obj

    def test_inspect_and_stale_check_without_attributes_datacrc(self):
        host, obj = self.host()
        self.assertFalse(hasattr(obj.Attributes, 'DataCRC'))
        item = host.inspect('one')
        host.check_original(item)
        obj.Attributes.payload['layer'] = 2
        with self.assertRaises(alpha.PreflightError):
            host.check_original(item)

    def test_restore_compares_serialized_attributes_and_userdata(self):
        host, obj = self.host()
        item = host.inspect('one')
        obj.Attributes.payload['userdata']['original'] = False
        host.restore(item)
        self.assertEqual(obj.Attributes.payload, {'layer': 1, 'userdata': {'original': True}})
        host.check_original(item)

    def test_mapping_without_datacrc_detects_runtime_transform_change(self):
        host, obj = self.host()
        mapping = SerializedOnly({'type': 'plane', 'channel': 1})
        mapping.PrimitiveTransform = Matrix()
        mapping.UvwTransform = Matrix()
        obj.GetTextureChannels = lambda: [1]
        obj.GetTextureMapping = lambda channel, transform: (mapping, Matrix())
        before = host.mapping_signature(obj)
        mapping.PrimitiveTransform = Matrix(3)
        self.assertNotEqual(before, host.mapping_signature(obj))
        mapping.PrimitiveTransform = Matrix()
        mapping.payload['type'] = 'box'
        self.assertNotEqual(before, host.mapping_signature(obj))


if __name__ == '__main__':
    unittest.main()
