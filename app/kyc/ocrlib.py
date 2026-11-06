import cv2, numpy as np, pytesseract, re
def load(path): return cv2.imread(path)
def text_mask(img):
    # dark text only: drop red watermark / light background
    b,g,r = [img[:,:,i].astype(int) for i in range(3)]
    return ((r<120)&(g<120)&(b<140)).astype(np.uint8)*255
def deskew(img):
    m = text_mask(img)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT,(25,3)))
    ys,xs = np.nonzero(m)
    if len(xs)<500: return img, 0.0
    best, bs = 0.0, -1
    # projection-profile search for rotation angle
    small = cv2.resize(m,None,fx=0.4,fy=0.4)
    h,w = small.shape
    for a in np.arange(-15,15.01,0.5):
        M = cv2.getRotationMatrix2D((w/2,h/2),a,1)
        rot = cv2.warpAffine(small,M,(w,h))
        s = np.var(rot.sum(axis=1))
        if s>bs: bs,best=s,a
    H,W = img.shape[:2]
    M = cv2.getRotationMatrix2D((W/2,H/2),best,1)
    out = cv2.warpAffine(img,M,(W,H),borderValue=(255,255,255))
    return out, best
def sharpen(img):
    g = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    bl = cv2.GaussianBlur(g,(0,0),3)
    s = cv2.addWeighted(g,2.5,bl,-1.5,0)
    return s
def ocr(img_gray, psm=6, whitelist=None):
    cfg=f"--oem 3 --psm {psm}"
    if whitelist: cfg+=f" -c tessedit_char_whitelist={whitelist}"
    return pytesseract.image_to_string(img_gray, config=cfg)
