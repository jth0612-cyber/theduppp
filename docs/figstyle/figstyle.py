# -*- coding: utf-8 -*-
"""Common look for figures drawn for the concept book (matplotlib).
usage:
    from figstyle import *
    fig, ax = new_fig(115, 55)          # size in mm (main text column is 115 mm wide)
    ... draw with C['blue'] etc ...
    save(fig, 'fig06_1.png')            # 600 dpi PNG with white background into scratchpad/figs/
Rules: flat colours from C, thin dark-gray outlines (0.6 pt), Korean labels in Pretendard 7-8 pt, no title inside the figure,
no drop shadows / gradients / 3D, arrows in C['pink'] like the book's bullet arrows, graph axes with arrow heads and italic-free labels."""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import patches

C = dict(ink='#231F20', gray='#808080', lgray='#DCDDDD', blue='#7FA2CF', dblue='#3F6DB0', lblue='#DFF2FC', teal='#009FBB',
         pink='#E79AA3', red='#D9534F', orange='#F2A65A', yellow='#FBD98B', green='#8CC084', purple='#A58BC6', brown='#B08A64', white='#FFFFFF')
FIGDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'figs')
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams.update({
    'font.family': ['Pretendard', 'Malgun Gothic'], 'font.size': 7.5, 'axes.unicode_minus': False,
    'axes.linewidth': 0.6, 'axes.edgecolor': C['ink'], 'axes.labelcolor': C['ink'], 'text.color': C['ink'],
    'xtick.color': C['ink'], 'ytick.color': C['ink'], 'xtick.major.width': 0.5, 'ytick.major.width': 0.5,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'lines.linewidth': 1.2, 'patch.linewidth': 0.6,
    'mathtext.fontset': 'stix', 'savefig.facecolor': 'white', 'figure.facecolor': 'white',
})


def new_fig(w_mm=115, h_mm=55, axes=True):
    fig = plt.figure(figsize=(w_mm / 25.4, h_mm / 25.4))
    if not axes:
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(0, w_mm); ax.set_ylim(0, h_mm)       # draw in mm coordinates
    else:
        ax = fig.add_subplot(111)
    return fig, ax


def graph_axes(ax, xlabel='', ylabel=''):
    """textbook style graph: only left/bottom spines with arrow heads, labels at the ends"""
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.plot(1, 0, '>', transform=ax.transAxes, clip_on=False, color=C['ink'], markersize=3)
    ax.plot(0, 1, '^', transform=ax.transAxes, clip_on=False, color=C['ink'], markersize=3)
    ax.set_xlabel(xlabel, loc='right'); ax.set_ylabel(ylabel, loc='top', rotation=0)


def box(ax, x, y, w, h, text='', fc=None, ec=None, fs=7.5, bold=False, r=1.2):
    p = patches.FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=%s' % r, fc=fc or C['lblue'], ec=ec or C['gray'], lw=0.6)
    ax.add_patch(p)
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, fontweight='bold' if bold else 'normal', linespacing=1.3)
    return p


def arrow(ax, x0, y0, x1, y1, color=None, lw=1.0, style='-|>'):
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle=style, color=color or C['pink'], lw=lw, shrinkA=0, shrinkB=0, mutation_scale=7))


def save(fig, name, dpi=600):
    path = os.path.join(FIGDIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    return path
