/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Read-only RF2 experiments derived from the pinned rf2-direct.c.
 * Modes: 0 baseline, 1 VCCIO 3.45, 2 gated/delayed OE, 3 descending,
 * 4 input pullups, 5 A9 rail routing. No programming commands. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <errno.h>
#include "minipro.h"
#include "t48.h"
int t48_set_vccio_voltagef(minipro_handle_t *,float,float);
static minipro_handle_t *h;
static uint8_t dir[56],state[56];
static pin_driver_t power[56];
static const int ap[]={8,7,6,5,4,3,2,1,23,22,19,21};
static int routed_a9=-1; static int mode; static unsigned capacity=2048;
static int address_bits=11;
static const int dp[]={9,10,11,13,14,15,16,17};
static volatile sig_atomic_t interrupted;
static int z(int pin) { return (pin<=12 ? pin : pin+16)-1; }
static void on_signal(int n) { interrupted=n; }
static void fail(const char *s) {
 fprintf(stderr,"ERROR: %s\n",s);
 if(h) { int r=minipro_reset_state(h); fprintf(stderr,"Reset pin drivers: %s\n",r?"FAILED":"OK"); minipro_close(h); }
 exit(1);
}
#define OK(x) do {if((x)) fail(#x);} while(0)
static void delay(long ns) {struct timespec t={ns/1000000000,ns%1000000000}; while(nanosleep(&t,&t)) { if(errno!=EINTR) fail("nanosleep"); }}
static double now(void) {struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static void address(unsigned a) { for(int i=0;i<address_bits;i++) state[z(ap[i])]=(a>>i)&1; }
static void configure(int writing,unsigned a,uint8_t b) {
 memset(dir,MP_PIN_DIRECTION_IN,sizeof dir); memset(state,0,sizeof state);
 for(int i=0;i<address_bits;i++) dir[z(ap[i])]=MP_PIN_DIRECTION_OUT;
 dir[z(18)]=dir[z(20)]=MP_PIN_DIRECTION_OUT;
 state[z(20)]=writing?1:0; /* OE high before data outputs enabled. */
 for(int i=0;i<8;i++) {dir[z(dp[i])]=writing?MP_PIN_DIRECTION_OUT:MP_PIN_DIRECTION_IN;state[z(dp[i])]=(b>>i)&1;}
 if(mode==4) dir[z(9)]|=0x80;
 if(mode==5) dir[z(22)]=MP_PIN_DIRECTION_IN;
 if(mode==11) memset(dir,MP_PIN_DIRECTION_IN,sizeof dir);
 address(a); OK(minipro_set_zif_direction(h,dir)); OK(minipro_set_zif_state(h,state));
}
static void rail_check(int programming) {
 float v[4];OK(t48_measure_voltages(h,v));
 fprintf(stderr,"ADC VPP=%.2f VCC=%.2f USB=%.2f VCCIO=%.2f\n",v[0],v[2],v[1],v[3]);
 if(v[2]<4.75||v[2]>5.25) fail("VCC outside RF2 range");
 if(programming&&(v[0]<23.5||v[0]>25.5)) fail("VPP outside RF2 range");
}
static void read_power(void) {
 /* Disconnect VPP before connecting the same pin to VCC. */
 memset(power,0,sizeof power);power[z(12)].gnd=1;power[z(24)].vcc=1;
 if(mode==11) {power[z(18)].gnd=1;power[z(20)].vcc=1;}
 OK(minipro_set_pin_drivers(h,power));
 if(capacity==2048) {power[z(21)].vcc=1; OK(minipro_set_pin_drivers(h,power));}
 OK(t48_set_vcc_voltagef(h,mode==6?5.18:5.0,0.1)); delay(1000000);
 configure(0,mode==9?0x200:0,0);
 if(mode==1 || mode==6) OK(t48_set_vccio_voltagef(h,3.45,0.01));
}
static uint8_t read_byte(unsigned a) {
 uint8_t pins[56];
 if(mode==11) {
  power[z(20)].gnd=0;power[z(20)].vcc=0;OK(minipro_set_pin_drivers(h,power));
  power[z(20)].vcc=1;OK(minipro_set_pin_drivers(h,power));
  for(int i=0;i<11;i++) {power[z(ap[i])].vcc=0;power[z(ap[i])].gnd=0;}
  OK(minipro_set_pin_drivers(h,power));
  for(int i=0;i<11;i++) {power[z(ap[i])].vcc=(a>>i)&1;power[z(ap[i])].gnd=!((a>>i)&1);}
  OK(minipro_set_pin_drivers(h,power));delay(1000000);
  power[z(20)].vcc=0;OK(minipro_set_pin_drivers(h,power));
  power[z(20)].gnd=1;OK(minipro_set_pin_drivers(h,power));delay(1000000);
 }
 if(mode==7) {state[z(18)]=1;state[z(20)]=1;OK(minipro_set_zif_state(h,state));delay(1000000);}
 if(mode==8) {configure(0,a,0);delay(1000000);}
 if(mode==5 && routed_a9!=((a>>9)&1)) {
  state[z(20)]=1;OK(minipro_set_zif_state(h,state));
  power[z(22)].vcc=0;power[z(22)].gnd=0;OK(minipro_set_pin_drivers(h,power));
  routed_a9=(a>>9)&1;
  power[z(22)].vcc=routed_a9;power[z(22)].gnd=!routed_a9;
  OK(minipro_set_pin_drivers(h,power));delay(1000000);
  state[z(20)]=0;
 }
 if(mode==2) {state[z(20)]=1;OK(minipro_set_zif_state(h,state));}
 address(a);OK(minipro_set_zif_state(h,state));delay(mode==2?1000000:10000);
 if(mode==7) {delay(1000000);state[z(18)]=0;state[z(20)]=0;OK(minipro_set_zif_state(h,state));delay(1000000);}
 if(mode==2) {state[z(20)]=0;OK(minipro_set_zif_state(h,state));delay(1000000);}
 OK(minipro_get_zif_state(h,pins));
 if((a&0x1ff)==0x50) fprintf(stderr,"Address=%04x A9-command=%u A9-digital-sense=%u\n",a,(a>>9)&1,pins[z(22)]);
 uint8_t b=0;for(int i=0;i<8;i++) b|=pins[z(dp[i])]<<i;return b;
}
static void read_all(uint8_t *b) {for(unsigned a=0;a<capacity;a++){if(interrupted)fail("interrupted");unsigned addr=mode==3?capacity-1-a:mode==9?(a^0x200):mode==10?(((a&0x3ff)>>1)|((a&1)<<9)|(a&0x400)):a;b[addr]=read_byte(addr);}}
static void save(const char *name,uint8_t *b) {FILE*f=fopen(name,"wb");if(!f)fail("open output");if(fwrite(b,1,capacity,f)!=capacity)fail("write output");if(fclose(f))fail("close output");}

int main(int argc,char **argv) {
 if(argc!=5 || strcmp(argv[1],"--serial")) return 2;
 mode=atoi(argv[4]); if(mode<0||mode>11) return 2;
 signal(SIGINT,on_signal);signal(SIGTERM,on_signal);signal(SIGHUP,on_signal);
 h=minipro_open(1);if(!h)return 1;
 if(h->version!=MP_T48||strcmp(h->serial_number,argv[2])) {minipro_close(h);return 1;}
 h->device=calloc(1,sizeof(*h->device));if(!h->device)fail("allocate device");
 h->device->package_details.pin_count=24; h->device->code_memory_size=2048;
 pin_map_t map={0};map.gnd_count=1;map.gnd_table[0]=12;map.mask_count=24;
 for(int i=0;i<24;i++)map.mask[i]=z(i+1)+1;
 OK(t48_pin_test(h,&map)); OK(minipro_reset_state(h));configure(0,mode==9?0x200:0,0);read_power();rail_check(0);
 uint8_t after[2048];read_all(after);
 OK(minipro_reset_state(h));save(argv[3],after);
 fprintf(stderr,"Reset pin drivers: OK; read-only mode=%d\n",mode);
 minipro_close(h);h=NULL;return 0;
}
