import os
import argparse

from domain.PointCloud import PointCloud
from domain.OLC import OLC
from domain.PPL import PPL
from domain.PPLplus import PPLplus

from static import Variable

from utils.read_write_model import *

cur_dir = os.path.abspath(os.path.dirname(__file__))

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def parseArgument():
    parser = argparse.ArgumentParser(description='Process Colmap Localization & Recover Images.')
    parser.add_argument('-d', '--dataset', type=str,
                        help='Colmap dataset to run localization test. [gerrald_hall, graham_hall, person_hall, south_building]',
                        default="apt1_living")

    parser.add_argument('-e','--estimate', type = str2bool, default = False, help = 'estimate pose if True')
    parser.add_argument('-r','--recover', type = str2bool, default = True, help = 'recover image if True')
    parser.add_argument('-t','--test', type = str2bool, default = True, help = 'test the results if True')
    parser.add_argument('-o','--onlyinv',type=str2bool,default=False, help = 'InvSfM only')
    parser.add_argument('-i','--invsfm', type = str2bool, default = True, help = 'reconstruct the images if True')
    parser.add_argument('-g','--gpus',type=str,default='cuda:0',help='Choose among cpu, cuda:0~4')

    args = parser.parse_args()

    print("***********************************************")
    print("Running Localization with Colmap Dataset: ", args.dataset)
    print()

    return args.dataset, args.estimate, args.recover, args.invsfm, args.test, args.onlyinv, args.gpus


def main():
    dataset, estimate_pose, recover_pts, recon_img, test, onlyinv, device = parseArgument()
    
    Variable.raise_errors(dataset)
    
    instances = []
    for inst in Variable.LINE_TYPE:
        if inst.lower() == "pc":
            instances.append(PointCloud(cur_dir, dataset))

        elif inst.lower() == "olc":
            instances.append(OLC(cur_dir, dataset))

        elif inst.lower() == "ppl":
            instances.append(PPL(cur_dir, dataset))

        elif inst.lower() == "pplplus":
            instances.append(PPLplus(cur_dir, dataset))
        
        else:
            raise Exception("Map type not supported", inst)

    if not onlyinv:
        for inst in instances:
            inst.makeLineCloud()

            # Sparsity only: noise level = 0
            # Noise only: sparisty level = 1
            # Sparsity & Noise: set any float to sparsity & noise level
            for sparsity_level in Variable.SPARSITY_LEVEL:
                inst.maskSparsity(sparsity_level)

                # Note that NOISE_LEVEL should have at least one value for this to run
                # To turn off noise effect, erase other intensity levels, keeping only zero. 
                for noise_level in Variable.NOISE_LEVEL:
                    if estimate_pose:
                        for query_id in inst.queryIds:
                            inst.matchCorrespondences(query_id)
                            inst.addNoise(noise_level)
                            inst.estimatePose(query_id)
                        
                        inst.savePose(sparsity_level, noise_level)

                    if recover_pts:
                        for esttype in Variable.ESTIMATOR:
                            inst.recoverPts(esttype, sparsity_level, noise_level)

                    if test:
                        for esttype in Variable.ESTIMATOR:
                            inst.test(recover_pts,esttype)

    if onlyinv or recon_img:
        for inst in instances:
            for sp in Variable.SPARSITY_LEVEL:
                for n in Variable.NOISE_LEVEL:
                    for est in Variable.ESTIMATOR:
                        for sw in Variable.SWAP_RATIO:
                            if inst.map_type=='PC':
                                est = 'noest'
                            inst.append_filenames(sp,n,est,sw)
            inst.checkexists()
            inst.reconImg(device)

# Sample Command
# python main.py -d gerrard_hall -e true -r false -t false
if __name__ == "__main__":
    main()
