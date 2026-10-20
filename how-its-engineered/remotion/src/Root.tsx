import React from 'react';
import { Composition } from 'remotion';
import { DT, DT_FRAMES } from './scenes/DT';
import { W, H, FPS } from './lib/core';

export const Root: React.FC = () => (
  <Composition id="DistributedTransactions" component={DT} durationInFrames={DT_FRAMES} fps={FPS} width={W} height={H} />
);
