import warnings 
warnings.filterwarnings('ignore')

import sys
sys.path.append('.')
sys.path.append('..')
import yaml 
import argparse
import traceback
import time
import torch

from model.models import STSSL
from model.trainer import Trainer
from lib.dataloader import get_dataloader
from lib.utils import (
    init_seed,
    get_model_params,
    load_graph, 
)


def model_supervisor(args):
    init_seed(args.seed)
    if not torch.cuda.is_available():
        args.device = 'cpu'
    
    ## load dataset
    dataloader = get_dataloader(
        data_dir=args.data_dir, 
        dataset=args.dataset, 
        batch_size=args.batch_size, 
        test_batch_size=args.test_batch_size,
        scalar_type='Standard'
    )
    graph = load_graph(args.graph_file, device=args.device)
    args.num_nodes = len(graph)
    
    ## init model and set optimizer
    model = STSSL(args).to(args.device)
    model_parameters = get_model_params([model])
    optimizer = torch.optim.Adam(
        params=model_parameters, 
        lr=args.lr_init, 
        eps=1.0e-8, 
        weight_decay=0, 
        amsgrad=False
    )

    ## start training
    trainer = Trainer(
        model=model, 
        optimizer=optimizer, 
        dataloader=dataloader,
        graph=graph, 
        args=args
    )
    results = None
    try:
        if args.mode == 'train':
            results = trainer.train() # best_eval_loss, best_epoch
        elif args.mode == 'test':
            # test
            state_dict = torch.load(
                args.best_path,
                map_location=torch.device(args.device)
            )
            model.load_state_dict(state_dict['model'])
            print("Load saved model")
            results = trainer.test(model, dataloader['test'], dataloader['scaler'],
                        graph, trainer.logger, trainer.args)
        else:
            raise ValueError
    except:
        trainer.logger.info(traceback.format_exc())
    return results

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_filename', '-cf', default='configs/NYCTaxi.yaml', 
                    type=str, help='the configuration to use')
    parser.add_argument('--S_Loss', default=0, type=int, help='use S_Loss or not')
    parser.add_argument('--T_Loss', default=0, type=int, help='use T_Loss or not')
    parser.add_argument('--seed', "-s", default=1, type=int, help='random seed to use')
    parser.add_argument('--comment', "-c", default="noComment", type=str, help='comment about the experiment')
    parser.add_argument('--cheb_order', "-K", default=3, type=int, help='calculate the chebyshev polynomials up to this order')
    parser.add_argument('--graph_init', "-g", default="neighbours", type=str, help='how to initialize the learnable graph')

    """
    if you pass bool flags in cli it will automatically make it true, irrespective if you pass True or False. If you dont pass it then it uses the default value.
    """
    parser.add_argument('--self_attention_flag', "-sa", default=False, type=bool, help='wether to self attention before pred')
    parser.add_argument('--cross_attention_flag', "-ca", default=False, type=bool, help='wether to cross attention before pred')
    parser.add_argument('--feedforward_flag', "-ff", default=False, type=bool, help='wether to feedforward')
    parser.add_argument('--layer_norm_flag', "-ln", default=False, type=bool, help='wether to layernorm')
    parser.add_argument('--additional_sa_flag', "-asa", default=False, type=bool, help='wether to additional SA')
    parser.add_argument('--learnable_flag', "-l", default=False, type=bool, help='wether to use learnable adj matrix')
    parser.add_argument('--rank', "-r", default=0, type=int, help='rank of adj matrix')
    parser.add_argument('--pos_emb_flag', "-pef", default=False, type=bool, help='wether to add pos_emb')

    # parser.add_argument('--input_length', default=0, type=int, help='# of samples to use for context')
    args = parser.parse_args()
    print(f'Starting experiment with configurations in {args.config_filename}...')
    
    time.sleep(3)
    configs = yaml.load(
        open(args.config_filename), 
        Loader=yaml.FullLoader
    )
    configs['S_Loss'] = args.S_Loss
    configs['T_Loss'] = args.T_Loss
    configs['seed'] = args.seed
    configs['comment'] = args.comment
    configs['cheb_order'] = args.cheb_order
    configs['graph_init'] = args.graph_init
    configs['self_attention_flag'] = args.self_attention_flag
    configs['cross_attention_flag'] = args.cross_attention_flag
    configs['feedforward_flag'] = args.feedforward_flag
    configs['layer_norm_flag'] = args.layer_norm_flag
    configs['additional_sa_flag'] = args.additional_sa_flag
    configs['learnable_flag'] = args.learnable_flag
    configs['pos_emb_flag'] = args.pos_emb_flag
    configs['rank'] = args.rank
    # configs['input_length'] = args.input_length
    # experimentName = "pred_" + str(args.input_length) + "_"
    experimentName = "pred_"
    if args.S_Loss == 1:
        experimentName += "+S"

    if args.T_Loss == 1:
        experimentName += "+T"
    experimentName += f"_seed={args.seed}"
    
    configs["experimentName"] = experimentName
    print(f'Starting experiment with configurations {configs}...')
    args = argparse.Namespace(**configs)
    model_supervisor(args)