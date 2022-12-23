from time import time
from bot import bot, status_dict, status_dict_lock, LOGGER
from bot.helper.ext_utils.message_utils import sendStatusMessage, update_all_messages
from bot.helper.mirror_leech_utils.status_utils.tg_download_status import TelegramStatus

class TelegramDownloader:
    def __init__(self, file, client, listener, path, name, multi=0, multi_zip=False) -> None:
        self.__client= client
        self.__listener = listener
        self.name = name
        self.gid = ''
        self.size = 0
        self.progress = 0
        self.downloaded_bytes = 0
        self.__file = file
        self.__path= path
        self.__start_time = time()
        self.__multi= multi
        self.__multi_zip= multi_zip
        self.__is_cancelled = False

    @property
    def download_speed(self):
        return self.downloaded_bytes / (time() - self.__start_time)

    async def __onDownloadStart(self, name, size, file_id):
        self.name = name
        self.size = size
        self.gid = file_id
        async with status_dict_lock:
            status_dict[self.__listener.uid] = TelegramStatus(self, self.__listener.message, self.gid)
        self.__listener.onDownloadStart()
        await sendStatusMessage(self.__listener.message)

    async def onDownloadProgress(self, current, total):
        if self.__is_cancelled:
            bot.stop_transmission()
            return
        self.downloaded_bytes = current
        try:
            self.progress = current / self.size * 100
        except ZeroDivisionError:
            pass

    async def download(self):
        if self.__multi_zip:
            if self.name == "":
                name = "multizip"
            else:
                name = self.name
            self.__path= self.__path
        else:
            if self.name == "":
                name = self.__file.file_name
            else:
                name = self.name
                self.__path = self.__path + name
        size = self.__file.file_size   
        gid = self.__file.file_unique_id
        await self.__onDownloadStart(name, size, gid)
        LOGGER.info(f'Downloading Telegram file with id: {gid}')
        try:
            download= await self.__client.download_media(
                message= self.__file,
                file_name= self.__path,
                progress= self.onDownloadProgress)
            if self.__is_cancelled:
                await self.__onDownloadError("Cancelled by user")
            if download is not None:
                if self.__multi_zip:
                    if self.__multi == 1:
                        await self.__listener.onMultiZipComplete()
                    else:
                        async with status_dict_lock:
                            del status_dict[self.__listener.uid]
                        await update_all_messages()
                else:
                    await self.__listener.onDownloadComplete()
        except Exception as e:
            await self.__onDownloadError(str(e))

    async def __onDownloadError(self, error):
        await self.__listener.onDownloadError(error) 

    def cancel_download(self):
        LOGGER.info(f'Cancelling download by user request')
        self.__is_cancelled = True

    

    