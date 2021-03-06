#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""

"""
from micropsi_core import runtime as micropsi
import pytest

__author__ = 'joscha'
__date__ = '29.10.12'


def prepare_nodenet(test_nodenet):
    res, node_a_uid = micropsi.add_node(test_nodenet, "Pipe", [200, 250, 10], None, state=None, name="A")
    res, node_b_uid = micropsi.add_node(test_nodenet, "Pipe", [500, 350, 10], None, state=None, name="B")
    res, node_c_uid = micropsi.add_node(test_nodenet, "Pipe", [300, 150, 10], None, state=None, name="C")
    res, node_s_uid = micropsi.add_node(test_nodenet, "Sensor", [200, 450, 10], None, state=None, name="S")
    return {
        'a': node_a_uid,
        'b': node_b_uid,
        'c': node_c_uid,
        's': node_s_uid
    }


def test_add_node(test_nodenet):
    micropsi.load_nodenet(test_nodenet)
    # make sure nodenet is empty
    nodespace = micropsi.get_nodes(test_nodenet)
    try:
        for i in nodespace["nodes"]:
            micropsi.delete_node(test_nodenet, i)
    except:
        pass

    nodespace = micropsi.get_nodes(test_nodenet)
    assert len(nodespace.get("nodes", [])) == 0
    res, uid = micropsi.add_node(test_nodenet, "Pipe", [200, 250, 10], None, state=None, name="A")
    nodespace = micropsi.get_nodes(test_nodenet)
    assert len(nodespace["nodes"]) == 1
    node1 = nodespace["nodes"][uid]
    assert node1["name"] == "A"
    assert node1["position"] == [200, 250, 10]


def test_position_always_3d(test_nodenet):
    res, nuid = micropsi.add_node(test_nodenet, "Pipe", [200], None, state=None, name="A")
    res, nsuid = micropsi.add_nodespace(test_nodenet, [200, 125, 0, 134], None, name="NS")
    data = micropsi.get_nodes(test_nodenet)
    assert data['nodes'][nuid]['position'] == [200, 0, 0]
    assert data['nodespaces'][nsuid]['position'] == [200, 125, 0]


def test_get_nodenet_activation_data(test_nodenet):
    nodes = prepare_nodenet(test_nodenet)
    uid = nodes['a']
    activation_data = micropsi.get_nodenet_activation_data(test_nodenet, [None])
    assert activation_data["activations"][uid][0] == 0
    assert activation_data["activations"][uid][1] == 0
    assert activation_data["activations"][uid][2] == 0
    assert activation_data["activations"][uid][3] == 0
    assert activation_data["activations"][uid][4] == 0
    assert activation_data["activations"][uid][5] == 0
    assert activation_data["activations"][uid][6] == 0

    micropsi.set_node_activation(test_nodenet, nodes['a'], 0.34556865)

    activation_data = micropsi.get_nodenet_activation_data(test_nodenet, [None])
    assert activation_data["activations"][uid][0] == 0.3


def test_get_nodenet_activation_data_for_nodespace(test_nodenet):
    nodes = prepare_nodenet(test_nodenet)
    uid = nodes['a']
    nodespace = micropsi.nodenets[test_nodenet].get_nodespace_uids()[0]
    activation_data = micropsi.get_nodenet_activation_data(test_nodenet, [nodespace])
    assert activation_data["activations"][uid][0] == 0


def test_get_nodespace(test_nodenet):
    nodes = prepare_nodenet(test_nodenet)
    nodespace = micropsi.get_nodes(test_nodenet)
    assert len(nodespace["nodes"]) == 4
    node1 = nodespace["nodes"][nodes['a']]
    assert node1["name"] == "A"
    assert node1["position"] == [200, 250, 10]


def test_get_nodespace_list(test_nodenet):
    nodes = prepare_nodenet(test_nodenet)
    data = micropsi.get_nodespace_list(test_nodenet)
    uid = list(data.keys())[0]
    assert data[uid]['name'] == 'Root'
    assert nodes['a'] in data[uid]['nodes']
    node = data[uid]['nodes'][nodes['a']]
    assert node['name'] == 'A'
    assert node['type'] == 'Pipe'


def test_get_nodespace_list_with_empty_nodespace(test_nodenet):
    res, uid = micropsi.add_nodespace(test_nodenet, [200, 250, 10], None, name="Foospace")
    data = micropsi.get_nodespace_list(test_nodenet)
    assert data[uid]['nodes'] == {}


def test_add_link(test_nodenet):
    nodes = prepare_nodenet(test_nodenet)
    micropsi.add_link(test_nodenet, nodes['a'], "por", nodes['b'], "gen", 0.5, 1)
    micropsi.add_link(test_nodenet, nodes['a'], "por", nodes['b'], "gen", 1, 0.1)
    micropsi.add_link(test_nodenet, nodes['c'], "ret", nodes['b'], "gen", 1, 1)

    nodespace = micropsi.get_nodes(test_nodenet)
    assert len(nodespace["nodes"]) == 4

    link_a_b = nodespace["nodes"][nodes['a']]['links']['por'][0]
    assert link_a_b['target_node_uid'] == nodes['b']
    assert link_a_b['target_slot_name'] == 'gen'
    assert link_a_b['weight'] == 1

    link_c_b = nodespace['nodes'][nodes['c']]['links']['ret'][0]
    assert link_c_b["target_node_uid"] == nodes['b']
    assert link_c_b["target_slot_name"] == "gen"

    assert nodespace['nodes'][nodes['b']]['links'] == {}
    assert nodespace['nodes'][nodes['s']]['links'] == {}


def test_delete_link(test_nodenet):
    nodes = prepare_nodenet(test_nodenet)
    success, link = micropsi.add_link(test_nodenet, nodes['a'], "por", nodes['b'], "gen", 0.5, 1)
    assert success
    micropsi.delete_link(test_nodenet, nodes['a'], "por", nodes['b'], "gen")
    nodespace = micropsi.get_nodes(test_nodenet)
    assert nodespace['nodes'][nodes['a']]['links'] == {}


def test_save_nodenet(test_nodenet):
    prepare_nodenet(test_nodenet)
    # save_nodenet
    micropsi.save_nodenet(test_nodenet)
    # unload_nodenet
    micropsi.unload_nodenet(test_nodenet)
    try:
        micropsi.get_nodes(test_nodenet)
        assert False, "could fetch a Nodespace that should not have been in memory"
    except:
        pass
    # load_nodenet
    micropsi.get_nodenet(test_nodenet)
    nodespace = micropsi.get_nodes(test_nodenet)
    assert len(nodespace["nodes"]) == 4
    micropsi.delete_nodenet(test_nodenet)


def test_reload_native_modules(fixed_nodenet):
    def hashlink(l):
        return "%s:%s:%s:%s" % (l['source_node_uid'], l['source_gate_name'], l['target_node_uid'], l['target_slot_name'])
    data_before = micropsi.nodenets[fixed_nodenet].export_json()
    links_before = set([hashlink(l) for l in data_before.pop('links')])
    micropsi.reload_native_modules()
    data_after = micropsi.nodenets[fixed_nodenet].export_json()
    links_after = set([hashlink(l) for l in data_after.pop('links')])
    assert data_before == data_after
    assert links_before == links_after


def test_native_module_and_recipe_categories(fixed_nodenet, resourcepath):
    import os
    os.mkdir(os.path.join(resourcepath, 'Test', 'Test2'))
    nodetype_file = os.path.join(resourcepath, 'Test', 'nodetypes.json')
    nodefunc_file = os.path.join(resourcepath, 'Test', 'nodefunctions.py')
    recipe_file = os.path.join(resourcepath, 'Test', 'Test2', 'recipes.py')
    with open(nodetype_file, 'w') as fp:
        fp.write('{"Testnode": {\
            "name": "Testnode",\
            "slottypes": ["gen", "foo", "bar"],\
            "nodefunction_name": "testnodefunc",\
            "gatetypes": ["gen", "foo", "bar"]\
            }}')
    with open(nodefunc_file, 'w') as fp:
        fp.write("def testnodefunc(netapi, node=None, **prams):\r\n    return 17")
    with open(recipe_file, 'w') as fp:
        fp.write("def testrecipe(netapi):\r\n    pass")
    micropsi.reload_native_modules()
    res = micropsi.get_available_native_module_types(fixed_nodenet)
    assert res['Testnode']['category'] == 'Test'
    res = micropsi.get_available_recipes()
    assert res['testrecipe']['category'] == 'Test/Test2'


@pytest.mark.engine("dict_engine")
# This behavior is not available in theano_engine: Default inheritance at runtime is not implemented for
# performance reasons, changed defaults will only affect newly created nodes.
# This test will have to be replaced when the generic solution proposed in TOL-90 has been
# implemented.
def test_gate_defaults_change_with_nodetype(fixed_nodenet, resourcepath,):
    # gate_parameters are a property of the nodetype, and should change with
    # the nodetype definition if not explicitly overwritten for a given node
    import os
    nodetype_file = os.path.join(resourcepath, 'Test', 'nodetypes.json')
    nodefunc_file = os.path.join(resourcepath, 'Test', 'nodefunctions.py')
    with open(nodetype_file, 'w') as fp:
        fp.write('{"Testnode": {\
            "name": "Testnode",\
            "slottypes": ["gen", "foo", "bar"],\
            "nodefunction_name": "testnodefunc",\
            "gatetypes": ["gen", "foo", "bar"],\
            "symbol": "t",\
            "gate_defaults":{\
              "foo": {\
                "amplification": 13\
              }\
            }}}')
    with open(nodefunc_file, 'w') as fp:
        fp.write("def testnodefunc(netapi, node=None, **prams):\r\n    return 17")
    micropsi.reload_native_modules()
    res, uid = micropsi.add_node(fixed_nodenet, "Testnode", [10, 10], name="Testnode")
    with open(nodetype_file, 'w') as fp:
        fp.write('{"Testnode": {\
            "name": "Testnode",\
            "slottypes": ["gen", "foo", "bar"],\
            "nodefunction_name": "testnodefunc",\
            "gatetypes": ["gen", "foo", "bar"],\
            "symbol": "t",\
            "gate_defaults":{\
              "foo": {\
                "amplification": 5\
              }\
            }}}')
    micropsi.reload_native_modules()
    params = micropsi.nodenets[fixed_nodenet].get_node(uid).get_gate_parameters()
    assert params["foo"]["amplification"] == 5


def test_non_standard_gate_defaults(test_nodenet):
    nodenet = micropsi.nodenets[test_nodenet]
    res, uid = micropsi.add_node(test_nodenet, 'Register', [30, 30, 10], name='test')
    node = nodenet.netapi.get_node(uid)
    genparams = {'maximum': 0.5}
    micropsi.set_gate_parameters(nodenet.uid, node.uid, 'gen', genparams)
    assert node.clone_non_default_gate_parameters()['gen']['maximum'] == 0.5
    assert node.get_data()['gate_parameters'] == {'gen': {'maximum': 0.5}}
    assert nodenet.get_data()['nodes'][uid]['gate_parameters'] == {'gen': {'maximum': 0.5}}
    data = micropsi.get_nodes(test_nodenet)
    assert data['nodes'][uid]['gate_parameters'] == {'gen': {'maximum': 0.5}}


def test_ignore_links(test_nodenet):
    nodes = prepare_nodenet(test_nodenet)
    micropsi.add_link(test_nodenet, nodes['a'], "por", nodes['b'], "gen", 0.5, 1)

    nodespace = micropsi.get_nodes(test_nodenet, [])
    assert len(nodespace["nodes"]) == 4
    assert 'links' not in nodespace

    assert len(nodespace["nodes"][nodes['a']]['links']['por']) == 1
    nodespace = micropsi.get_nodes(test_nodenet, [], include_links=False)
    assert 'links' not in nodespace["nodes"][nodes['a']]


def test_remove_and_reload_native_module(fixed_nodenet, resourcepath):
    import os
    nodetype_file = os.path.join(resourcepath, 'Test', 'nodetypes.json')
    nodefunc_file = os.path.join(resourcepath, 'Test', 'nodefunctions.py')
    with open(nodetype_file, 'w') as fp:
        fp.write('{"Testnode": {\
            "name": "Testnode",\
            "slottypes": ["gen", "foo", "bar"],\
            "nodefunction_name": "testnodefunc",\
            "gatetypes": ["gen", "foo", "bar"],\
            "symbol": "t",\
            "gate_defaults":{\
              "foo": {\
                "amplification": 13\
              }\
            }}}')
    with open(nodefunc_file, 'w') as fp:
        fp.write("def testnodefunc(netapi, node=None, **prams):\r\n    return 17")

    micropsi.reload_native_modules()
    res, uid = micropsi.add_node(fixed_nodenet, "Testnode", [10, 10, 10], name="Testnode")
    os.remove(nodetype_file)
    os.remove(nodefunc_file)
    micropsi.reload_native_modules()
    assert 'Testnode' not in micropsi.get_available_native_module_types(fixed_nodenet)


@pytest.mark.engine("dict_engine")
def test_engine_specific_nodetype_dict(fixed_nodenet, resourcepath):
    import os
    nodetype_file = os.path.join(resourcepath, 'Test', 'nodetypes.json')
    nodefunc_file = os.path.join(resourcepath, 'Test', 'nodefunctions.py')
    with open(nodetype_file, 'w') as fp:
        fp.write('{"Testnode": {\
            "engine": "theano_engine",\
            "name": "Testnode",\
            "slottypes": ["gen", "foo", "bar"],\
            "nodefunction_name": "testnodefunc",\
            "gatetypes": ["gen", "foo", "bar"],\
            "symbol": "t",\
            "gate_defaults":{\
              "foo": {\
                "amplification": 13\
              }\
            }}}')
    with open(nodefunc_file, 'w') as fp:
        fp.write("def testnodefunc(netapi, node=None, **prams):\r\n    return 17")

    micropsi.reload_native_modules()
    data = micropsi.get_nodenet_metadata(fixed_nodenet)
    assert "Testnode" not in data['native_modules']


@pytest.mark.engine("theano_engine")
def test_engine_specific_nodetype_theano(fixed_nodenet, resourcepath):
    import os
    nodetype_file = os.path.join(resourcepath, 'Test', 'nodetypes.json')
    nodefunc_file = os.path.join(resourcepath, 'Test', 'nodefunctions.py')
    with open(nodetype_file, 'w') as fp:
        fp.write('{"Testnode": {\
            "engine": "dict_engine",\
            "name": "Testnode",\
            "slottypes": ["gen", "foo", "bar"],\
            "nodefunction_name": "testnodefunc",\
            "gatetypes": ["gen", "foo", "bar"],\
            "symbol": "t",\
            "gate_defaults":{\
              "foo": {\
                "amplification": 13\
              }\
            }}}')
    with open(nodefunc_file, 'w') as fp:
        fp.write("def testnodefunc(netapi, node=None, **prams):\r\n    return 17")

    micropsi.reload_native_modules()
    data = micropsi.get_nodenet_metadata(fixed_nodenet)
    assert "Testnode" not in data['native_modules']


def test_node_parameters_none_resets_to_default(fixed_nodenet):
    nodenet = micropsi.nodenets[fixed_nodenet]
    res, uid = micropsi.add_node(fixed_nodenet, 'Pipe', [30, 30, 10], name='test')
    node = nodenet.netapi.get_node(uid)
    micropsi.set_node_parameters(fixed_nodenet, node.uid, {'expectation': '', 'wait': 0})
    assert node.get_parameter('expectation') == 1
    assert node.get_parameter('wait') == 0


def test_get_recipes(fixed_nodenet, resourcepath):
    import os
    recipe_file = os.path.join(resourcepath, 'Test', 'recipes.py')
    with open(recipe_file, 'w') as fp:
        fp.write("""
def testfoo(netapi, count=23):
    return {'count':count}
""")
    micropsi.reload_native_modules()
    recipes = micropsi.get_available_recipes()
    assert 'testfoo' in recipes
    assert len(recipes['testfoo']['parameters']) == 1
    assert recipes['testfoo']['parameters'][0]['name'] == 'count'
    assert recipes['testfoo']['parameters'][0]['default'] == 23


def test_run_recipe(fixed_nodenet, resourcepath):
    import os
    recipe_file = os.path.join(resourcepath, 'Test', 'recipes.py')
    with open(recipe_file, 'w') as fp:
        fp.write("""
def testfoo(netapi, count=23):
    return {'count':count}
""")
    micropsi.reload_native_modules()
    state, result = micropsi.run_recipe(fixed_nodenet, 'testfoo', {'count': 42})
    assert state
    assert result['count'] == 42


def test_node_parameter_defaults(fixed_nodenet, resourcepath):
    import os
    nodetype_file = os.path.join(resourcepath, 'Test', 'nodetypes.json')
    nodefunc_file = os.path.join(resourcepath, 'Test', 'nodefunctions.py')
    with open(nodetype_file, 'w') as fp:
        fp.write('{"Testnode": {\
            "name": "Testnode",\
            "slottypes": ["gen", "foo", "bar"],\
            "gatetypes": ["gen", "foo", "bar"],\
            "nodefunction_name": "testnodefunc",\
            "parameters": ["testparam"],\
            "parameter_defaults": {\
                "testparam": 13\
              }\
            }}')
    with open(nodefunc_file, 'w') as fp:
        fp.write("def testnodefunc(netapi, node=None, **prams):\r\n    return 17")

    micropsi.reload_native_modules()
    res, uid = micropsi.add_node(fixed_nodenet, "Testnode", [10, 10, 10], name="Test")
    node = micropsi.nodenets[fixed_nodenet].get_node(uid)
    assert node.get_parameter("testparam") == 13


def test_node_parameters_from_persistence(fixed_nodenet, resourcepath):
    import os
    nodetype_file = os.path.join(resourcepath, 'Test', 'nodetypes.json')
    nodefunc_file = os.path.join(resourcepath, 'Test', 'nodefunctions.py')
    with open(nodetype_file, 'w') as fp:
        fp.write('{"Testnode": {\
            "name": "Testnode",\
            "slottypes": ["gen", "foo", "bar"],\
            "gatetypes": ["gen", "foo", "bar"],\
            "nodefunction_name": "testnodefunc",\
            "parameters": ["testparam"],\
            "parameter_defaults": {\
                "testparam": 13\
              }\
            }}')
    with open(nodefunc_file, 'w') as fp:
        fp.write("def testnodefunc(netapi, node=None, **prams):\r\n    return 17")
    micropsi.reload_native_modules()
    res, uid = micropsi.add_node(fixed_nodenet, "Testnode", [10, 10, 10], name="Test")
    node = micropsi.nodenets[fixed_nodenet].get_node(uid)
    node.set_parameter("testparam", 42)
    micropsi.save_nodenet(fixed_nodenet)
    micropsi.revert_nodenet(fixed_nodenet)
    node = micropsi.nodenets[fixed_nodenet].get_node(uid)
    assert node.get_parameter("testparam") == 42
