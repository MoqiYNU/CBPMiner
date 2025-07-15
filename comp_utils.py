# coding=gbk
from net import Flow, Marking, OpenNet
import net_gen as ng
import net_utils as nu
import net as nt
import comp_utils as cu
'''
  ��������ϵĹ�����
  1.��������˳��,ѡ��,�����͵������(��link�ṹ);
  2.�����ṹֻ��repeat-until�ṹ;
  3.������ͬ��+�첽��;
  4.ps:ÿ����Դ������Ӧһ����Դ;
  5.�漰ʱ����Ϣ.
'''


# 0.����Ͽ���������Դӳ��Ϊ����--------------------------------------------------
def res_to_places(comp_net: OpenNet):
    '''
    Note:Ĭ��ÿ����Դ������Ӧһ����Դ
    '''
    init_res = comp_net.init_res
    source = comp_net.source
    new_source = Marking(source.get_infor() + init_res)
    comp_net.source = new_source

    res_places = comp_net.res_places
    comp_net.add_places(res_places)

    req_res_map = comp_net.req_res_map
    for tran, req_res in req_res_map.items():
        for res in req_res:
            comp_net.add_flow(res, tran)
    rel_res_map = comp_net.rel_res_map
    for tran, rel_res in rel_res_map.items():
        for res in rel_res:
            comp_net.add_flow(tran, res)

    return comp_net


# ��ȡcom_net�б�Ǩ�ڰ�������Ϣ,����ÿ����Դת��Ϊһ������
def get_case_infor(nets, comp_net: OpenNet):
    tran_infor = {}
    trans = comp_net.trans
    for tran in trans:
        tran_infor[tran] = {
            'rec_msg':
            list(
                set(nt.get_preset(comp_net.flows, tran))
                & set(comp_net.msg_places)),
            'send_msg':
            list(
                set(nt.get_postset(comp_net.flows, tran))
                & set(comp_net.msg_places)),
            'req_res':
            list(
                set(nt.get_preset(comp_net.flows, tran))
                & set(comp_net.res_places)),
            'rel_res':
            list(
                set(nt.get_postset(comp_net.flows, tran))
                & set(comp_net.res_places)),
            'roles':
            get_roles(tran, nets),
        }
    return tran_infor


def get_roles(tran, nets):
    roles = []
    trans = tran.split('_')
    for t in trans:
        for net in nets:
            if t in net.trans:
                roles.append(net.role)
                break
    return roles


# 1a.��Ͽ�����(ͬ��+�첽)--------------------------------------------
'''
���������Ҫ�����ڽ�ģ,����PIPE�н�ģ�������кϲ�
'''


def get_compose_net(nets):
    # gen_sync_transΪ�ϲ������е��м�ͬ����Ǩ��
    gen_sync_trans = []
    net = compose_nets(nets, gen_sync_trans)
    print('gen_sync_trans: ', gen_sync_trans)
    net.print_infor()
    return net


# 1.1a.���bag���������---------------------------------------------
def compose_nets(nets, gen_sync_trans):
    if len(nets) == 0:
        print('no bag_nets exist, exit...')
        return
    if len(nets) == 1:
        return nets[0]
    else:
        net = compose_two_nets(nets[0], nets[1], gen_sync_trans)
        for i in range(2, len(nets)):
            net = compose_two_nets(net, nets[i], gen_sync_trans)
        return net


# �������������
def compose_two_nets(net1: OpenNet, net2: OpenNet, gen_sync_trans):

    # 1)����Դ����ֹ��ʶ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    source1, sinks1 = net1.get_start_ends()
    source2, sinks2 = net2.get_start_ends()
    source = Marking(source1.get_infor() + source2.get_infor())
    sinks = []
    for sink1 in sinks1:
        for sink2 in sinks2:
            sink = Marking(sink1.get_infor() + sink2.get_infor())
            sinks.append(sink)

    # 2)��������(�����ظ�)~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    places1, inner_places1, msg_places1 = net1.get_places()
    places2, inner_places2, msg_places2 = net2.get_places()
    places = list(set(places1 + places2))
    inner_places = list(set(inner_places1 + inner_places2))
    msg_places = list(set(msg_places1 + msg_places2))

    # 3)������Դ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    res_places1, res_property1, req_res_map1, rel_res_map1 = net1.get_res_places(
    )
    res_places2, res_property2, req_res_map2, rel_res_map2 = net2.get_res_places(
    )
    res_places = list(set(res_places1 + res_places2))
    shared_res = set(res_places1).intersection(set(res_places2))
    res_property = {}
    for res, pro in res_property1.items():
        res_property[res] = pro
    # ����������Դ
    for res, pro in res_property2.items():
        if res in shared_res:
            continue
        res_property[res] = pro
    # �ڲ�����Ǩ�й���
    req_res_map = {}
    rel_res_map = {}

    init_res = []
    init_res1 = net1.get_init_res()
    init_res2 = net2.get_init_res()
    for res in init_res1:
        init_res.append(res)
    # ����������Դ
    for res in init_res2:
        if res in shared_res:
            continue
        init_res.append(res)

    # 4)������Ǩ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    trans1, rout_trans1, tran_label_map1 = net1.get_trans()
    trans2, rout_trans2, tran_label_map2 = net2.get_trans()
    sync_trans1, sync_trans2 = get_sync_trans(net1, net2)
    trans = []
    tran_label_map = {}
    tran_delay_map = {}

    # a)net1��net2�з�ͬ����Ǩ
    for tran1 in trans1:
        if tran1 not in sync_trans1:
            trans.append(tran1)
            tran_label_map[tran1] = tran_label_map1[tran1]
            # ps:���úϲ���Ǩʱ����
            print('error:', net1.tran_delay_map[tran1])
            tran_delay_map[tran1] = net1.tran_delay_map[tran1]
            # net1�з�ͬ����Ǩ������/�ͷ���Դ
            req_res_map[tran1] = req_res_map1[tran1]
            rel_res_map[tran1] = rel_res_map1[tran1]
    for tran2 in trans2:
        if tran2 not in sync_trans2:
            trans.append(tran2)
            tran_label_map[tran2] = tran_label_map2[tran2]
            # ps:���úϲ���Ǩʱ����
            tran_delay_map[tran2] = net2.tran_delay_map[tran2]
            # net2�з�ͬ����Ǩ������/�ͷ���Դ
            req_res_map[tran2] = req_res_map2[tran2]
            rel_res_map[tran2] = rel_res_map2[tran2]

    # b)net1��net2��ͬ����Ǩ(Note:��������ͬ���ϲ���Ǩ,����һ����Ǩ���ԲμӶ��ͬ���)
    syncMap1 = []
    syncMap2 = []

    print('sync_trans: ', sync_trans1, sync_trans2)

    for sync_tran1 in sync_trans1:

        # sync_trans�洢net2����sync_tran1ͬ��(�����ͬ)��Ǩ�Ƽ�
        sync_trans_in_net2 = []

        for sync_tran2 in sync_trans2:
            if tran_label_map1[sync_tran1] == tran_label_map2[sync_tran2]:
                sync_trans_in_net2.append(sync_tran2)

        if sync_tran1 in gen_sync_trans:
            gen_sync_trans.remove(sync_tran1)

        for sync_tran in sync_trans_in_net2:

            if sync_tran in gen_sync_trans:
                gen_sync_trans.remove(sync_tran)

            # ͬ����ǨId�ϲ�:a_b
            gen_sync_tran = sync_tran1 + '_' + sync_tran
            trans.append(gen_sync_tran)
            tran_label_map[gen_sync_tran] = tran_label_map1[sync_tran1]
            # ps:���úϲ���Ǩʱ����
            tran_delay_map[gen_sync_tran] = net1.tran_delay_map[sync_tran1]

            # Note:�ϲ�ͬ����Ǩ�ж����Ǩ������/�ͷ���Դ~~~~~~~~~~~~~~~~~~~
            # ps:ÿ����Դ������Ӧһ����Դ,��������ͬ��Դ���ǹ�����Դ
            req_res_map[gen_sync_tran] = list(
                set(req_res_map1[sync_tran1] + req_res_map2[sync_tran]))
            rel_res_map[gen_sync_tran] = list(
                set(rel_res_map1[sync_tran1] + rel_res_map2[sync_tran]))

            gen_sync_trans.append(gen_sync_tran)

            syncMap1.append([sync_tran1, gen_sync_tran])
            syncMap2.append([sync_tran, gen_sync_tran])

    print('gen_sync_trans: ', gen_sync_trans)
    rout_trans = list(set(rout_trans1 + rout_trans2))

    # 5)��������ϵ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    flows = []
    flows1 = net1.get_flows()
    flows2 = net2.get_flows()

    # ps:Ҫ�����ظ������ͬ����Ǩ���ɵ���(����֯����Ϣ������)
    for flow in flows1:

        flow_from, flow_to = flow.get_infor()

        if flow_from in sync_trans1:
            merge_trans = get_merge_trans(flow_from, syncMap1)
            for merge_tran in merge_trans:
                if not flow_is_exist(flows, merge_tran, flow_to):
                    flows.append(Flow(merge_tran, flow_to))
        elif flow_to in sync_trans1:
            merge_trans = get_merge_trans(flow_to, syncMap1)
            for merge_tran in merge_trans:
                if not flow_is_exist(flows, flow_from, merge_tran):
                    flows.append(Flow(flow_from, merge_tran))
        else:
            flows.append(flow)

    for flow in flows2:

        flow_from, flow_to = flow.get_infor()

        if flow_from in sync_trans2:
            merge_trans = get_merge_trans(flow_from, syncMap2)
            for merge_tran in merge_trans:
                if not flow_is_exist(flows, merge_tran, flow_to):
                    flows.append(Flow(merge_tran, flow_to))
        elif flow_to in sync_trans2:
            merge_trans = get_merge_trans(flow_to, syncMap2)
            for merge_tran in merge_trans:
                if not flow_is_exist(flows, flow_from, merge_tran):
                    flows.append(Flow(flow_from, merge_tran))
        else:
            flows.append(flow)

    openNet = OpenNet(source, sinks, places, trans, tran_label_map, flows)
    openNet.inner_places = inner_places
    openNet.msg_places = msg_places
    openNet.rout_trans = rout_trans
    openNet.init_res = init_res
    openNet.res_places = res_places
    openNet.res_property = res_property
    openNet.req_res_map = req_res_map
    openNet.rel_res_map = rel_res_map
    openNet.tran_delay_map = tran_delay_map
    return openNet


# ��ȡͬ���кϲ�Ǩ�Ƽ�
def get_merge_trans(tran, syncMap):
    merge_trans = []
    for item in syncMap:
        if item[0] == tran:
            merge_trans.append(item[1])
    return merge_trans


# �ֱ��ȡnet1��net2��ͬ��Ǩ�Ƽ�
def get_sync_trans(net1, net2):
    sync_trans1 = []
    sync_trans2 = []
    trans1, rout_trans1, label_map1 = net1.get_trans()
    trans2, rout_trans2, label_map2 = net2.get_trans()
    for tran1 in trans1:
        # �ų����Ʊ�Ǩ
        if tran1 in rout_trans1:
            continue
        if is_sync_tran(tran1, net1, net2):
            sync_trans1.append(tran1)
    for tran2 in trans2:
        # �ų����Ʊ�Ǩ
        if tran2 in rout_trans2:
            continue
        if is_sync_tran(tran2, net2, net1):
            sync_trans2.append(tran2)
    return sync_trans1, sync_trans2


# �ж�tran1�ǲ���ͬ����Ǩ
def is_sync_tran(tran1, net1, net2):
    trans1, rout_trans1, tran_label_map1 = net1.get_trans()
    trans2, rout_trans2, tran_label_map2 = net2.get_trans()
    label1 = tran_label_map1[tran1]
    for tran2 in trans2:
        # �ų����Ʊ�Ǩ
        if tran2 in rout_trans2:
            continue
        label2 = tran_label_map2[tran2]
        if label1 == label2:
            return True
    return False


# �ж�ĳ�����Ƿ����
def flow_is_exist(flows, flow_from, flow_to):
    for temp_flow in flows:
        temp_flow_from, temp_flow_to = temp_flow.get_infor()
        if temp_flow_from == flow_from and temp_flow_to == flow_to:
            return True
    return False


# 1b.��úϲ�������(�첽)-----------------------------------------------
'''
���������Ҫ�����ڽ��ھ��õ������кϲ�
'''


def get_compose_net_async(nets):
    if len(nets) == 0:
        print('no bag_nets exist, exit...')
        return
    if len(nets) == 1:
        return nets[0]
    else:
        net = compose_two_nets_async(nets[0], nets[1])
        for i in range(2, len(nets)):
            net = compose_two_nets_async(net, nets[i])
        return net


# �첽�ϲ�����������
def compose_two_nets_async(net1: OpenNet, net2: OpenNet):

    # 1)����Դ����ֹ��ʶ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    source1, sinks1 = net1.get_start_ends()
    source2, sinks2 = net2.get_start_ends()
    # ps:�����ظ������Ϣ������Դ(��Ϣ����Դ���Գ�ʼ����)
    source = Marking(list(set(source1.get_infor() + source2.get_infor())))
    sinks = []
    for sink1 in sinks1:
        for sink2 in sinks2:
            sink = Marking(sink1.get_infor() + sink2.get_infor())
            sinks.append(sink)

    # 2)��������(�����ظ�)~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    places1, inner_places1, msg_places1 = net1.get_places()
    places2, inner_places2, msg_places2 = net2.get_places()
    places = list(set(places1 + places2))
    inner_places = list(set(inner_places1 + inner_places2))
    msg_places = list(set(msg_places1 + msg_places2))

    # 3)������Դ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    res_places = list(set(net1.res_places + net2.res_places))

    # 4)������Ǩ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    trans1, rout_trans1, tran_label_map1 = net1.get_trans()
    trans2, rout_trans2, tran_label_map2 = net2.get_trans()
    trans = []
    tran_label_map = {}
    # tran_delay_map = {}

    # net1��net2�б�Ǩ
    for tran1 in trans1:
        trans.append(tran1)
        tran_label_map[tran1] = tran_label_map1[tran1]
        # ps:���úϲ���Ǩʱ����
        # tran_delay_map[tran1] = net1.tran_delay_map[tran1]
    for tran2 in trans2:
        if tran2 in trans1:  #ps:�����ظ�ͬ����Ǩ
            continue
        trans.append(tran2)
        tran_label_map[tran2] = tran_label_map2[tran2]
        # ps:���úϲ���Ǩʱ����
        # tran_delay_map[tran2] = net2.tran_delay_map[tran2]

    # 5)��������ϵ(���������ͬ����Ǩ���µ��ظ���)~~~~~~~~~~~~~
    flows = []
    flows1 = net1.get_flows()
    for flow in flows1:
        flow_from, flow_to = flow.get_infor()
        if not flow_is_exist(flows, flow_from, flow_to):
            flows.append(flow)
    flows2 = net2.get_flows()
    for flow in flows2:
        flow_from, flow_to = flow.get_infor()
        if not flow_is_exist(flows, flow_from, flow_to):
            flows.append(flow)

    openNet = OpenNet(source, sinks, places, trans, tran_label_map, flows)
    openNet.inner_places = inner_places
    openNet.msg_places = msg_places
    openNet.res_places = res_places
    # openNet.tran_delay_map = tran_delay_map
    return openNet


# -------------------------------����---------------------------------#

if __name__ == '__main__':

    # path = '/Users/moqi/Desktop/ԭʼģ��/���Ų���/IMPL_����.xml'

    # path = '/Users/moqi/Desktop/ԭʼģ��/�����ھ�/HIS.xml'
    # path = '/Users/moqi/Desktop/ԭʼģ��/�����ھ�/Example 1.xml'
    path = '/Users/moqi/Desktop/ԭʼģ��/�����ھ�/Example 1.xml'

    nets = ng.gen_nets(path)
    comp_net = get_compose_net(nets)
    comp_net = cu.res_to_places(comp_net)
    print('dep:', len(nets), 'tran:', len(comp_net.trans), 'msg:',
          len(comp_net.msg_places), 'res:', len(comp_net.res_places), 'opt:',
          len(comp_net.sinks))

    comp_net.net_to_dot('comp_net', False)

    rg = nu.gen_rg(comp_net)
    lts = rg.rg_to_lts()[0]
    lts.lts_to_dot()

# -------------------------------------------------------------------#
