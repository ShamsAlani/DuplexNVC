# Phase 2 Step 2 settings (sourced by 2a/2b/2c/2r). name -> model id, model input, video size
S2="$WORK/phase2/step2"; MP4="$WORK/data/vcd_1080p/mp4/th"; NV="$WORK/data/nv12"; INCD="$WORK/data/incoming"
CK_MLVC=~/mlvc/job-outputs/pretrained/mlvc-psnr-v1.ckpt
CK_MLVCS=~/mlvc/job-outputs/pretrained/mlvc-s-psnr-v1.ckpt
CAMIDS="0380a333cb0fef69001fb4260e2a705f 6587aeba8bb9bc97c0fc640ee664c444"
INCIDS="6c9c96d33030b3b3879c691760492b14 9c02f633262ef15f81eab1f2fa06faa5"
NEW="mlvc_540p mlvc_720p mlvc_1080p mlvcs_540p mlvcs_720p mlvcs_1080p"
cfg () {  # sets MODEL CKPT MSIZE VSIZE RES for a setting name
  case $1 in mlvc_*) MODEL=dmc61sbr_reglu; CKPT=$CK_MLVC;; mlvcs_*) MODEL=dmc61sbr_mini_reglu; CKPT=$CK_MLVCS;; esac
  case $1 in *_360p|mlvc_multi) MSIZE=640x368; VSIZE=640x360; RES=360p;;
             *_540p) MSIZE=960x544; VSIZE=960x540; RES=540p;;
             *_720p) MSIZE=1280x720; VSIZE=1280x720; RES=720p;;
             *_1080p) MSIZE=1920x1088; VSIZE=1920x1080; RES=1080p;; esac
}
# bundle folder, camera stream and incoming stream per setting
bund () { case $1 in mlvc_360p) echo "$WORK/bundles/mlvc";; *) echo "$WORK/bundles/$1";; esac; }
camf () { cfg $1; [ $RES = 360p ] && echo "$CAM" || echo "$NV/cam_$RES.nv12"; }
incf () { case $1 in mlvc_360p|mlvc_multi) echo "$BINC/incoming.aus";; *) echo "$INCD/$1-qp26/incoming.aus";; esac; }
