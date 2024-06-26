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
        scalar_type='Standard',
        input_dataset_context=args.input_dataset_context,
        input_sequence_type=args.input_sequence_type
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
    parser.add_argument('--config_filename', default='configs/NYCBike1.yaml', 
                    type=str, help='the configuration to use')
    parser.add_argument('--S_Loss', default=0, type=int, help='use S_Loss or not')
    parser.add_argument('--T_Loss', default=0, type=int, help='use T_Loss or not')
    parser.add_argument('--seed', default=1, type=int, help='random seed to use')
    parser.add_argument('--input_dataset_context', default=0, type=int, help='# of samples in the original dataset')
    parser.add_argument('--input_sequence_type', default="F", type=str, help='which sequence to use for input')
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
    configs['input_dataset_context'] = args.input_dataset_context
    configs['input_sequence_type'] = args.input_sequence_type
    if args.input_sequence_type == "A" and args.input_dataset_context == 19:
        configs['input_length'] = 4
    elif args.input_sequence_type != "A" and args.input_dataset_context == 19: 
        configs['input_length'] = 5

    if args.input_sequence_type == "A" and args.input_dataset_context == 35:
        configs['input_length'] = 8
    elif args.input_sequence_type != "A" and args.input_dataset_context == 35: 
        configs['input_length'] = 9

    experimentName = "pred_" + str(configs['input_length']) + "_"
    if args.S_Loss == 1:
        experimentName += "+S"

    if args.T_Loss == 1:
        experimentName += "+T"
    experimentName += f"_seed={args.seed}"
    
    configs["experimentName"] = experimentName
    print(f'Starting experiment with configurations {configs}...')
    args = argparse.Namespace(**configs)
    model_supervisor(args)