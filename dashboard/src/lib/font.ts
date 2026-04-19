import {
  Inter_Tight,
  JetBrains_Mono,
  Instrument_Serif,
  Mulish
} from 'next/font/google';

import { cn } from '@/lib/utils';

const fontSans = Inter_Tight({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-sans'
});

const fontMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-mono'
});

const fontSerif = Instrument_Serif({
  subsets: ['latin'],
  weight: '400',
  style: ['normal', 'italic'],
  variable: '--font-serif'
});

const fontMullish = Mulish({
  subsets: ['latin'],
  variable: '--font-mullish'
});

export const fontVariables = cn(
  fontSans.variable,
  fontMono.variable,
  fontSerif.variable,
  fontMullish.variable
);
