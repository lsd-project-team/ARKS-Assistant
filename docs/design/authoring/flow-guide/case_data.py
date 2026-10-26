"""两册共用的说明输入与数学复算，不执行设备动作。"""
import math

def rotate(xy, degrees):
    a=math.radians(degrees);x,y=xy
    return (x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a))

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def display(xy):return '('+', '.join(f'{v:.3f}' for v in xy)+')'

CASE=dict(product='P1',runtime='N1',address='基板1／基岛2／A',chip='C1',
    tu_origin=(100,200),substrate=(20,0),island=(10,5),point=(10,5),
    s1_offset=(2,-1),height_delta=.12,product_translation=(.2,-.1),
    mark_axis=(200,100),mark_to_center=(.5,.2),pick_nozzle=(.05,-.02),pick_comp=(.01,.03),
    locate_angle=2,pick_hard_angle=5,nozzle_align=30,vision_angle=0,
    uplook_displacement=(.12,-.08),capture_minus_reference=(.02,-.01),
    uplook_center=(.5,.2),pr_angle=2,teach_angle=1,bond_angle=0,bond_hard_angle=1)

def compute():
    c=CASE
    initial=add(add(add(c['tu_origin'],c['substrate']),c['island']),c['point'])
    at_s1=add(initial,c['s1_offset'])
    localized=add(initial,c['product_translation'])
    pick_vector=rotate(c['mark_to_center'],-c['locate_angle'])
    pick_xy=sub(add(sub(c['mark_axis'],c['pick_nozzle']),c['pick_comp']),pick_vector)
    pick_t=c['pick_hard_angle']-c['locate_angle']+c['nozzle_align']
    photo_t=c['vision_angle']+c['nozzle_align']
    center=rotate(c['uplook_center'],-(c['pr_angle']-c['teach_angle']))
    saved=sub(add(c['uplook_displacement'],c['capture_minus_reference']),center)
    target_t=photo_t+c['pr_angle']+c['bond_angle']+c['bond_hard_angle']
    remaining=target_t-photo_t
    addition=rotate(saved,remaining)
    target=add(localized,addition)
    return dict(initial=initial,at_s1=at_s1,at_s1_height=(*at_s1,c['height_delta']),
        refreshed=(*initial,0),localized=localized,pick_vector=pick_vector,pick_xy=pick_xy,
        pick_t=pick_t,photo_t=photo_t,saved=saved,target_t=target_t,remaining=remaining,
        addition=addition,target_g0=target)

VALUES=compute()
