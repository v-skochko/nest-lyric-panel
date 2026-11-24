import {pipeline,env} from '@huggingface/transformers';
env.cacheDir='/model-cache';
try {
 const translate=await pipeline('translation','Xenova/opus-mt-en-uk',{dtype:'q8',local_files_only:false});
 process.send({type:'ready'});
 process.on('message',async msg=>{try{const values=[];for(const text of msg.input){const result=await translate(text,{max_new_tokens:256});values.push(result[0].translation_text)}process.send({id:msg.id,values})}catch(e){process.send({id:msg.id,error:String(e)})}});
} catch(e){console.error('Model startup failed:',e);process.exit(1)}
