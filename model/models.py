import torch.nn as nn
import torch
# import 
from lib.utils import masked_mae_loss
from model.aug import (
    aug_topology, 
    aug_traffic, 
)
from model.layers import (
    STEncoder, 
    SpatialHeteroModel, 
    TemporalHeteroModel, 
    MLP, 
)

class STSSL(nn.Module):
    def __init__(self, args):
        super(STSSL, self).__init__()
        # spatial temporal encoder
        self.encoderA = STEncoder(Kt=3, Ks=3, blocks=[[2, int(args.d_model//2), args.d_model], [args.d_model, int(args.d_model//2), args.d_model]], 
                        input_length=args.input_length, num_nodes=args.num_nodes, droprate=args.dropout)
        self.encoderB = STEncoder(Kt=3, Ks=3, blocks=[[2, int(args.d_model//2), args.d_model], [args.d_model, int(args.d_model//2), args.d_model]], 
                        input_length=args.input_length, num_nodes=args.num_nodes, droprate=args.dropout)
        self.encoderC = STEncoder(Kt=3, Ks=3, blocks=[[2, int(args.d_model//2), args.d_model], [args.d_model, int(args.d_model//2), args.d_model]], 
                        input_length=args.input_length, num_nodes=args.num_nodes, droprate=args.dropout)
        self.encoderD = STEncoder(Kt=3, Ks=3, blocks=[[2, int(args.d_model//2), args.d_model], [args.d_model, int(args.d_model//2), args.d_model]], 
                        input_length=args.input_length, num_nodes=args.num_nodes, droprate=args.dropout)
        
        self.channel_reducer1 = nn.Conv3d(in_channels=3, out_channels=1, kernel_size=(1, 1, 1), padding='same') ## padding='same' to keep output size same as input 
        self.channel_reducer2 = nn.Conv3d(in_channels=3, out_channels=1, kernel_size=(1, 1, 1), padding='same') ## padding='same' to keep output size same as input 
        self.channel_reducer = nn.Conv3d(in_channels=3, out_channels=1, kernel_size=(1, 1, 1), padding='same') ## padding='same' to keep output size same as input 

        # traffic flow prediction branch
        self.mlp = MLP(args.d_model, args.d_output)
        self.mlpRepr = MLP(3*args.d_model, args.d_model)
        # temporal heterogenrity modeling branch
        self.thm = TemporalHeteroModel(args.d_model, args.batch_size, args.num_nodes, args.device)
        # spatial heterogenrity modeling branch
        self.shm = SpatialHeteroModel(args.d_model, args.nmb_prototype, args.batch_size, args.shm_temp)
        self.mae = masked_mae_loss(mask_value=5.0)
        # self.mae = masked_mae_loss(mask_value=None)
        self.args = args
    
    def forward(self, view1, graph):
        # input_sequence_dict = {"A":[-4, 19], "B":[-9, -4], "C":[-14, -9], "D":[-19, -14]}
        # input_sequence_dict = {"A":[-8, 35], "B":[-17, -8], "C":[-26, -17], "D":[-35, -26]}
        # print("view1.shape: ", view1.shape, "graph.shape: ", graph.shape)  # view1.shape:  torch.Size([32, 19, 128, 2]) graph.shape:  torch.Size([128, 128])
        
        view1A = view1[:, -8:35, :, :]
        view1B = view1[:, -17:-8, :, :]
        view1C = view1[:, -26:-17, :, :]
        # view1D = view1[:, -35:-26, :, :]
        
        # view1A = view1[:, -4:19, :, :]
        # view1B = view1[:, -9:-4, :, :]
        # view1C = view1[:, -14:-9, :, :]
        # view1D = view1[:, -19:-14, :, :]
        

        # print("view1A.shape: ", view1A.shape, "view1B1.shape: ", view1B1.shape, "view1B2.shape: ", view1B2.shape, "view1B3.shape: ", view1B3.shape)
        # view1B = torch.cat((view1B1, view1B2, view1B3), dim=1)
        # print("\n\nview1B.shape: ", view1B.shape)  ## view1B.shape:  torch.Size([32, 3, 5, 128, 2])
        # view1BIN = view1B[..., 0].unsqueeze(-1)
        # print("view1BIN.shape: ", view1BIN.shape)  ## view1BIN.shape:  torch.Size([32, 3, 5, 128])  unsqueeze(-1) to get last dim back
        # view1BOUT = view1B[..., 1].unsqueeze(-1)
        
        # view1B = self.channel_reducer(view1B).squeeze(1)
        
        
        # view1BIN = self.channel_reducer1(view1BIN).squeeze(1)
        # view1BOUT = self.channel_reducer2(view1BOUT).squeeze(1)
        # view1B = torch.cat((view1BIN, view1BOUT), dim=-1)
        # print("view1B_reduced.shape: ", view1B_reduced.shape)
        repr1A = self.encoderA(view1A, graph) # view1: n,l,v,c; graph: v,v 
        repr1B = self.encoderB(view1B, graph) # view1: n,l,v,c; graph: v,v 
        repr1C = self.encoderC(view1C, graph) # view1: n,l,v,c; graph: v,v 
        # repr1D = self.encoderD(view1D, graph) # view1: n,l,v,c; graph: v,v 
        # print("repr1A.shape: ", repr1A.shape) # repr1A.shape:  torch.Size([32, 1, 128, 64])
        # print("repr1B.shape: ", repr1B.shape) # repr1B.shape:  torch.Size([32, 1, 128, 64])
        combined_repr = torch.cat((repr1A, repr1B, repr1C), dim=3)            ## combine along the channel dimension d_model
        ## now 2*d_model --> d_model
        # print("combined_repr.shape: ", combined_repr.shape)
        combined_repr = self.mlpRepr(combined_repr)
        # print("combined_repr.shape: ", combined_repr.shape)
        # s_sim_mx = self.fetch_spatial_sim()
        # graph2 = aug_topology(s_sim_mx, graph, percent=self.args.percent*2)
        
        # t_sim_mx = self.fetch_temporal_sim()
        # view2 = aug_traffic(t_sim_mx, view1, percent=self.args.percent)
        # print("view2.shape: ", view2.shape, "graph2.shape: ", graph2.shape)
        # repr2 = self.encoder(view2, graph2)
        repr2 = None
        return combined_repr, repr2

    def fetch_spatial_sim(self):
        """
        Fetch the region similarity matrix generated by region embedding.
        Note this can be called only when spatial_sim is True.
        :return sim_mx: tensor, similarity matrix, (v, v)
        """
        return self.encoder.s_sim_mx.cpu()
    
    def fetch_temporal_sim(self):
        return self.encoder.t_sim_mx.cpu()

    def predict(self, z1, z2):
        '''Predicting future traffic flow.
        :param z1, z2 (tensor): shape nvc
        :return: nlvc, l=1, c=2
        '''
        # print("z1.shape: ", z1.shape)
        return self.mlp(z1)

    def loss(self, z1, z2, y_true, scaler, loss_weights):
        l1 = self.pred_loss(z1, z2, y_true, scaler)
        sep_loss = [l1.item()]
        loss = loss_weights[0] * l1 

        # l2 = self.temporal_loss(z1, z2)
        # sep_loss.append(l2.item())
        # if self.args.T_Loss==1:
            # loss += loss_weights[1] * l2
        
        # l3 = self.spatial_loss(z1, z2)
        # sep_loss.append(l3.item())
        # if self.args.S_Loss==1:
            # print("spatial loss: ", l3)
            # loss += loss_weights[2] * l3 
        # print("predLoss: ", l1.item(), "temporalLoss: ", l2.item(), "spatialLoss: ", l3.item())
        return loss, sep_loss

    def pred_loss(self, z1, z2, y_true, scaler):
        y_pred = scaler.inverse_transform(self.predict(z1, z2))
        y_true = scaler.inverse_transform(y_true)
 
        loss = self.args.yita * self.mae(y_pred[..., 0], y_true[..., 0]) + \
                (1 - self.args.yita) * self.mae(y_pred[..., 1], y_true[..., 1])
        return loss
    
    def temporal_loss(self, z1, z2):
        return self.thm(z1, z2)

    def spatial_loss(self, z1, z2):
        return self.shm(z1, z2)
    