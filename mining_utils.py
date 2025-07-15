# coding=gbk
from ast import literal_eval
import pandas as pd
import pm4py
import net as nt
import copy
from lts import LTS


# 1.�Ȱ�case_id����,�ٶ�ÿ�������ڵ�tran��Ӧ��list����------------------------------
# �������ǻ������ֻ�ɱ�Ǩ��ɵĲ��ظ���cases
def gen_cases(df):
    grouped = df.groupby('case_id')['tran'].apply(list).reset_index()
    # ��ȡgrouped������tran��,��������ӵ��б�cases��
    cases = grouped['tran'].tolist()
    return cases


# 2.csv��־תΪdf���д���--------------------------------------------------
def csv_to_df(csv_file):
    df = pd.read_csv(csv_file)
    # ps:case_id���ַ�������
    df['case_id'] = df['case_id'].astype(str)
    # ��Ϣ,��Դ�ͽ�ɫ��list����
    df['rec_msg'] = df['rec_msg'].apply(literal_eval)
    df['send_msg'] = df['send_msg'].apply(literal_eval)
    df['req_res'] = df['req_res'].apply(literal_eval)
    df['rel_res'] = df['rel_res'].apply(literal_eval)
    df['roles'] = df['roles'].apply(literal_eval)
    # timestamp��datetime����
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(df)
    return df


# 3.���ݽ�ɫ����־�з�Ϊ����־-----------------------------------------------
def gen_sub_log(df, role):
    filtered_df = df[df['roles'].apply(lambda x: role in x)]
    return filtered_df


# 4.������н�ɫ����ѡ��ɫ---------------------------------------------------
def get_roles(df):
    # df = remove_duplicate_groups(df)
    roles = df['roles'].explode().unique().tolist()
    optional_roles = set()
    for case_id, group in df.groupby('case_id'):
        case_roles = group['roles'].explode().unique().tolist()
        optional_roles = optional_roles.union(set(roles) - set(case_roles))
    return roles, list(optional_roles)


# 5.���˵�������ͬ��Ǩ�б�ķ���,��������ԭʼ��--------------------------------
def remove_duplicate_groups(df,
                            group_col='case_id',
                            value_col='tran',
                            ignore_order=False):
    '''
    ����:
    df:ԭʼDataFrame
    group_col:��������
    value_col:���ڱȽϵ�ֵ����
    ignore_order:�Ƿ����ֵ��˳��(Ĭ��False,����˳��)
    ����:���˺��DataFrame
    '''
    seen = {}
    groups = df.groupby(group_col)
    unique_ids = []

    for name, group in groups:
        values = group[value_col].values

        # ����ignore_order���������Ƿ�����ֵ
        if ignore_order:
            values_sorted = sorted(values)
            key = tuple(values_sorted)
        else:
            key = tuple(values)

        # ������³��ֵ�ֵ��ϣ���������
        if key not in seen:
            seen[key] = True
            unique_ids.append(name)

    # ���ع��˺��DataFrame������ԭʼ�У�
    return df[df[group_col].isin(unique_ids)].reset_index(drop=True)


# 6.����IM�㷨�ھ�BP----------------------------------------------------
'''
�����ھ�ʽ:
1)������Ϣ,��Դ,��ѡBP�ķ���
2)������Ϣ����Դ,�����ǿ�ѡBP�ķ���
3)������Ϣ,��������Դ�Ϳ�ѡBP�ķ���
'''


def IHP_Discovery_all(sub_df, non_duplicate_df, marker, is_optional):
    net, im, fm = pm4py.discover_petri_net_inductive(sub_df,
                                                     activity_key='tran',
                                                     case_id_key='case_id',
                                                     timestamp_key='timestamp')
    # print(net, im, fm)
    # pm4py.view_petri_net(net, im, fm)

    places = []
    inner_places = []
    for temp_place in net.places:
        place = transform_name(temp_place.name, marker)
        places.append(place)
        inner_places.append(place)
    print('places', places, inner_places)

    trans = []
    label_map = {}
    for t in net.transitions:
        # t.nameΪ�ھ��㷨���������һ���ַ���,t.label����'t1','t2'
        tran = t.label
        # ps:Ҫע���Ǩ�������·�ɱ�Ǩ
        if tran is None:
            tran = transform_name(t.name, marker)
        trans.append(tran)
        label_map[tran] = tran
    print('trans', trans, label_map)

    flows = []
    for arc in net.arcs:
        if isinstance(arc.source, pm4py.objects.petri_net.obj.PetriNet.Place):
            flow_from = transform_name(arc.source.name, marker)
            flow_to = arc.target.label
            # ps:Ҫע���Ǩ�������·�ɱ�Ǩ
            if flow_to is None:
                flow_to = transform_name(arc.target.name, marker)
            # print(flow_from, flow_to)
            flows.append(nt.Flow(flow_from, flow_to))
        else:
            flow_from = arc.source.label
            # ps:Ҫע���Ǩ�������·�ɱ�Ǩ
            if flow_from is None:
                flow_from = transform_name(arc.source.name, marker)
            flow_to = transform_name(arc.target.name, marker)
            # print(flow_from, flow_to)
            flows.append(nt.Flow(flow_from, flow_to))

    msg_places = set()
    res_places = set()
    for tran in trans:
        # tran���ھ��������·�ɱ�Ǩû�ж�Ӧ����
        all_rows = non_duplicate_df[non_duplicate_df['tran'] == tran]
        if all_rows.empty:
            continue
        # ��һ��Ǩ��Ϊtran����
        row = all_rows.iloc[0]
        # ��ȡrec_msg�У�list���ͣ�
        rec_msg = row['rec_msg']
        msg_places = msg_places.union(set(rec_msg))
        for rec_msg_i in rec_msg:
            flows.append(nt.Flow(rec_msg_i, tran))
        # ��ȡsend_msg�У�list���ͣ�
        send_msg = row['send_msg']
        msg_places = msg_places.union(set(send_msg))
        for send_msg_i in send_msg:
            flows.append(nt.Flow(tran, send_msg_i))
        # ��ȡreq_res�У�list���ͣ�
        req_res = row['req_res']
        res_places = res_places.union(set(req_res))
        for req_res_i in req_res:
            flows.append(nt.Flow(req_res_i, tran))
        # ��ȡrel_res�У�list���ͣ�
        rel_res = row['rel_res']
        res_places = res_places.union(set(rel_res))
        for rel_res_i in rel_res:
            flows.append(nt.Flow(tran, rel_res_i))

    msg_places = list(msg_places)
    res_places = list(res_places)
    places = places + msg_places + res_places

    source = nt.Marking([transform_name('source', marker)])
    print(source)
    # ���ǿ�ѡBP,��source��sink��Ҫ����
    sinks = []
    if is_optional:
        sinks.append(nt.Marking([transform_name('source', marker)]))
        sinks.append(nt.Marking([transform_name('sink', marker)]))
    else:
        sinks.append(nt.Marking([transform_name('sink', marker)]))

    open_net = nt.OpenNet(source, sinks, places, trans, label_map, flows)
    open_net.inner_places = inner_places
    open_net.msg_places = msg_places
    open_net.res_places = res_places
    # open_net.net_to_dot('open_net{}'.format(marker), False)
    return open_net


# �������ַ���
def transform_name(name, marker):
    if '_' in name:
        # �ҵ���һ���»��ߵ�λ��
        idx = name.find('_')
        # �ָ��ַ��������м������
        return name[:idx] + f'_{marker}_' + name[idx + 1:]
    else:
        # ֱ����ӱ��
        return f'{name}_{marker}'


# 7.����־��ȡ��ʼ��Դ---------------------------------------------------
def get_init_res(df, res_places):
    init_res = []
    # ȥ��
    non_duplicate_df = remove_duplicate_groups(copy.deepcopy(df))
    for res in res_places:
        skip_outer = False
        for case_id, group in non_duplicate_df.groupby('case_id'):
            # ��ʱ�������(ȷ��˳�����)
            sorted_group = group.sort_values('timestamp')
            for index, row in sorted_group.iterrows():
                req_res = row['req_res']
                rel_res = row['rel_res']
                # �ȼ�����������Ϊ����{(res,t),(t,res)}
                if res in req_res:
                    # ������ʼ��Դ
                    init_res.append(res)
                    skip_outer = True
                    break  # ����������ѭ��
                elif res in rel_res:
                    # ���ǳ�ʼ��Դ
                    skip_outer = True
                    break  # ����������ѭ��
            if skip_outer:
                break  # �����ڶ���ѭ��

    return init_res


# ��һ��ltsת��Ϊ�ڽӱ�
def lts_to_adjacency_list(lts: LTS):
    adjacency_list = {}
    # ps:�ȳ�ʼ��ÿ���ڵ�
    for state in lts.states:
        adjacency_list[state] = []
    for tran in lts.trans:
        state_from, label, state_to = tran.get_infor()
        adjacency_list[state_from].append((state_to, label))
    return adjacency_list
