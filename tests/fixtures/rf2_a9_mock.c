/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Host-only state-machine test double; never opens USB.
 * Derived from the recorded mock-rails.c. A9 margin behavior is an explanatory
 * fault model, not an analog simulation or a measured silicon threshold.
 * The illustrative 5.05 cutoff separates the two tested requested settings.
 */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <time.h>
#include "minipro.h"
static minipro_handle_t h;
static unsigned char mem[4096],dirs[56],pins[56];
static pin_driver_t pwr[56];
static double ticks,pulse_start,vcc=5,vpp=25;
static int pulses;
static int z(int p){return(p<=12?p:p+16)-1;}
static unsigned addr(void){int a[]={8,7,6,5,4,3,2,1,23,22,19,21};unsigned v=0;for(int i=0;i<(h.device && h.device->code_memory_size==4096?12:11);i++)v|=(pwr[z(a[i])].vcc?1:pwr[z(a[i])].gnd?0:pins[z(a[i])])<<i;if(getenv("MOCK_A9_MARGIN") && !(dirs[z(22)]==MP_PIN_DIRECTION_IN && (pwr[z(22)].vcc||pwr[z(22)].gnd) && vcc>=5.05)) v&=~0x200u;return v;}
static unsigned data(void){int d[]={9,10,11,13,14,15,16,17};unsigned v=0;for(int i=0;i<8;i++)v|=pins[z(d[i])]<<i;return v;}
int clock_gettime(clockid_t id,struct timespec*t){(void)id;t->tv_sec=ticks;t->tv_nsec=(ticks-t->tv_sec)*1e9;return 0;}
int nanosleep(const struct timespec*t,struct timespec*r){(void)r;ticks+=t->tv_sec+t->tv_nsec/1e9;return 0;}
minipro_handle_t*minipro_open(uint8_t verbose){(void)verbose;memset(mem,255,sizeof mem);mem[0]=getenv("MOCK_INCOMPATIBLE")?0:0xc3;if(getenv("MOCK_2732"))for(int i=0;i<4096;i++)mem[i]=(i^(i>>8))&255;if(getenv("MOCK_IMAGE")) {FILE*f=fopen(getenv("MOCK_IMAGE"),"rb");assert(f);assert(fread(mem,1,2048,f)==2048);assert(fgetc(f)==EOF);fclose(f);}h.version=MP_T48;strcpy(h.serial_number,"6MNNWV7B0LLRDYCAA5PF5744");return &h;}
void minipro_close(minipro_handle_t*x){(void)x;for(int i=0;i<56;i++)assert(!pwr[i].vcc&&!pwr[i].vpp&&!pwr[i].gnd);if(getenv("MOCK_PHYSICAL_OUT")) {FILE*f=fopen(getenv("MOCK_PHYSICAL_OUT"),"wb");assert(f);assert(fwrite(mem,1,2048,f)==2048);assert(!fclose(f));}free(h.device);h.device=NULL;fprintf(stderr,"MOCK pulses=%d cleanup=OK\n",pulses);}
int minipro_reset_state(minipro_handle_t*x){(void)x;memset(pwr,0,sizeof pwr);memset(pins,0,sizeof pins);return 0;}
int minipro_set_zif_direction(minipro_handle_t*x,uint8_t*d){(void)x;memcpy(dirs,d,56);return 0;}
int minipro_set_zif_state(minipro_handle_t*x,uint8_t*s){(void)x;
 if(pwr[z(21)].vpp && !pins[z(18)] && s[z(18)]) {
  assert(s[z(20)]==1);assert(vpp>=23.5&&vpp<=25.5);assert(vcc>=4.75&&vcc<=5.25);
  pulse_start=ticks;pulses++;
 }
 if(pwr[z(21)].vpp && pins[z(18)] && !s[z(18)]) {
  assert(ticks-pulse_start>=0.04999&&ticks-pulse_start<=0.055);
  if(!getenv("MOCK_VERIFY_FAIL"))mem[addr()]&=data();
 }
 memcpy(pins,s,56);return 0;
}
int minipro_set_pin_drivers(minipro_handle_t*x,pin_driver_t*p){(void)x;
 for(int i=0;i<56;i++){assert(!(p[i].vcc&&p[i].vpp));assert(!(p[i].vcc&&p[i].gnd));assert(!(p[i].gnd&&pwr[i].vcc));assert(!(p[i].vcc&&pwr[i].gnd));assert(!(p[i].vcc&&pwr[i].vpp));}
 if(p[z(22)].vcc||p[z(22)].gnd)assert(dirs[z(22)]==MP_PIN_DIRECTION_IN);
 assert(p[z(12)].gnd);assert(p[z(24)].vcc);memcpy(pwr,p,sizeof pwr);return 0;
}
int minipro_get_zif_state(minipro_handle_t*x,uint8_t*s){(void)x;memcpy(s,pins,56);assert(!pwr[z(21)].vpp);if(h.device->code_memory_size==4096){assert(!pwr[z(21)].vcc);assert(dirs[z(21)]==MP_PIN_DIRECTION_OUT);assert(!pwr[z(20)].vpp);}else assert(pwr[z(21)].vcc);
 int d[]={9,10,11,13,14,15,16,17};for(int i=0;i<8;i++){assert(dirs[z(d[i])]==MP_PIN_DIRECTION_IN);s[z(d[i])]=(mem[addr()]>>i)&1;}return 0;
}
int t48_set_vcc_voltagef(minipro_handle_t*x,float v,float t){(void)x;(void)t;vcc=v;return 0;}
int t48_set_vpp_voltagef(minipro_handle_t*x,float v,float t){(void)x;(void)t;vpp=v;return 0;}
int t48_measure_voltages(minipro_handle_t*x,float*v){(void)x;v[0]=getenv("MOCK_OVERVOLT")?26:vpp;v[1]=5;v[2]=vcc;v[3]=3.3;return 0;}

int t48_pin_test(minipro_handle_t*x,pin_map_t*m){(void)x;assert(m->mask_count==24);return getenv("MOCK_CONTACT_FAIL")?1:0;}
