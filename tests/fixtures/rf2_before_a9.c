/* SPDX-License-Identifier: GPL-3.0-or-later */
/* T48 / standard DIP24 RF2 diagnostic writer. Links with minipro (GPL-3.0).
 * Fixed pinout, no erase, read-before-write, one 50 ms pulse, verify or stop.
 * Requires the pulldown cache-invalidation fix in accompanying minipro.patch.
 * An explicit expected serial is required. Default command only reads.
 */
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
static minipro_handle_t *h;
static uint8_t dir[56],state[56];
static pin_driver_t power[56];
static const int ap[]={8,7,6,5,4,3,2,1,23,22,19,21};
static unsigned capacity=2048;
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
 OK(minipro_set_pin_drivers(h,power));
 if(capacity==2048) {power[z(21)].vcc=1; OK(minipro_set_pin_drivers(h,power));}
 OK(t48_set_vcc_voltagef(h,5.0,0.1)); delay(1000000);
 configure(0,0,0);
}
static uint8_t read_byte(unsigned a) {
 uint8_t pins[56];address(a);OK(minipro_set_zif_state(h,state));delay(10000);
 OK(minipro_get_zif_state(h,pins));uint8_t b=0;for(int i=0;i<8;i++) b|=pins[z(dp[i])]<<i;return b;
}
static void read_all(uint8_t *b) {for(unsigned a=0;a<capacity;a++){if(interrupted)fail("interrupted");b[a]=read_byte(a);}}
static void save(const char *name,uint8_t *b) {FILE*f=fopen(name,"wb");if(!f)fail("open output");if(fwrite(b,1,capacity,f)!=capacity)fail("write output");if(fclose(f))fail("close output");}
int main(int argc,char **argv) {
 if(argc<3 || strcmp(argv[1],"--serial") || !argv[2][0]) {
  fprintf(stderr,"Required: --serial EXPECTED_T48_SERIAL read OUTPUT | read2732 OUTPUT | write INPUT OUTPUT MAX_CHANGED_BYTES\n");return 2;
 }
 const char *expected_serial=argv[2]; argc-=2; argv+=2;
 int writing=argc==5&&!strcmp(argv[1],"write");
 int reading2732=argc==3&&!strcmp(argv[1],"read2732");
 if(reading2732) {capacity=4096;address_bits=12;}
 if(!writing && !reading2732 && !(argc==3&&!strcmp(argv[1],"read"))) {fprintf(stderr,"Usage: rf2-direct read OUTPUT | read2732 OUTPUT | write INPUT OUTPUT MAX_CHANGED_BYTES\n");return 2;}
 uint8_t target[2048],before[4096],after[4096];unsigned limit=0;
 if(writing) {char *end;long n=strtol(argv[4],&end,10);if(*end||n<1||n>2048)return 2;limit=n;FILE*f=fopen(argv[2],"rb");if(!f)return 2;if(fread(target,1,2048,f)!=2048||fgetc(f)!=EOF){fclose(f);return 2;}fclose(f);}
 signal(SIGINT,on_signal);signal(SIGTERM,on_signal);signal(SIGHUP,on_signal);
 h=minipro_open(1);if(!h)return 1;
 if(h->version!=MP_T48||strcmp(h->serial_number,expected_serial)) {
  fprintf(stderr,"ERROR: wrong programmer; no pin commands sent\n"); minipro_close(h);h=NULL;return 1;
 }
 /* Diode contact preflight detects an empty/disconnected socket before power. */
 h->device=calloc(1,sizeof(*h->device));if(!h->device)fail("allocate device");
 h->device->package_details.pin_count=24;
 h->device->code_memory_size=capacity;
 pin_map_t map={0};map.gnd_count=1;map.gnd_table[0]=12;map.mask_count=24;
 for(int i=0;i<24;i++)map.mask[i]=z(i+1)+1;
 OK(t48_pin_test(h,&map));
 OK(minipro_reset_state(h)); configure(0,0,0); read_power(); rail_check(0);read_all(before);
 unsigned changed=0;
 if(writing) {
  for(unsigned a=0;a<2048;a++)if((before[a]&target[a])!=target[a])fail("target needs UV erase");
  for(unsigned a=0;a<2048&&changed<limit;a++) {
   if(before[a]==target[a])continue;
   if(interrupted)fail("interrupted");
   /* Disable outputs before driving the data bus. VPP is still at read voltage. */
   state[z(20)]=1;OK(minipro_set_zif_state(h,state));configure(1,a,target[a]);
   /* Disconnect read VPP=VCC, set generator, then connect programming VPP. */
   power[z(21)].vcc=0;OK(minipro_set_pin_drivers(h,power));
   OK(t48_set_vpp_voltagef(h,24.37,0.1));
   power[z(21)].vpp=1;OK(minipro_set_pin_drivers(h,power));
   OK(t48_set_vcc_voltagef(h,5.0,0.1));delay(2000000);
   rail_check(1);if(interrupted)fail("interrupted before pulse");
   state[z(18)]=1;double start=now();OK(minipro_set_zif_state(h,state));
   delay(50000000);state[z(18)]=0;OK(minipro_set_zif_state(h,state));double ms=(now()-start)*1000;
   delay(100000);read_power();uint8_t got=read_byte(a);
   fprintf(stderr,"%04x old=%02x want=%02x got=%02x host-pulse-window=%.3fms\n",a,before[a],target[a],got,ms);
   if(got!=target[a])fail("byte verification mismatch; no retry");
   changed++;
  }
 }
 read_all(after);
 OK(minipro_reset_state(h)); /* Power off before host filesystem operations. */
 save(writing?argv[3]:argv[2],after);
 unsigned mismatch=0;if(writing)for(int a=0;a<2048;a++)mismatch+=after[a]!=target[a];
 OK(minipro_reset_state(h));fprintf(stderr,"Reset pin drivers: OK; changed=%u remaining=%u\n",changed,mismatch);minipro_close(h);h=NULL;
 return writing&&mismatch?3:0;
}
